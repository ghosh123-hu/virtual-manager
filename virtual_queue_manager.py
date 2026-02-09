"""
Virtual Queue Manager (console simulation).

Confirmed facts from prompt:
- No existing backend is provided.
- Python only for logic and simulation.
- No real-time DB/SMS/payment integrations.
- Must support booking, token assignment, estimated wait time, serving, status view, and capacity checks.

Assumptions:
- "Daily capacity" is enforced per service as max bookings per day (served + waiting).
- Wait estimate is linear: number_of_people_ahead * average_service_time_minutes.
- Single-threaded simulation (no concurrent writes).

Design decisions:
- Use deque for O(1) enqueue/dequeue operations.
- Use dict for O(1) average-time lookup by service id and token id.
- Keep queue history snapshots for optional text graph (queue length vs event index).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Booking:
    token: str
    user_name: str
    service_id: str
    estimated_wait_minutes_at_booking: int


class ServiceQueue:
    """Queue state for one service type."""

    def __init__(self, service_id: str, display_name: str, daily_capacity: int, avg_service_minutes: int):
        self.service_id = service_id
        self.display_name = display_name
        self.daily_capacity = daily_capacity
        self.avg_service_minutes = avg_service_minutes

        # Waiting line for this service.
        self.waiting: Deque[Booking] = deque()
        self.total_bookings_created = 0
        self.next_token_number = 1
        self.served_count = 0

    def is_full(self) -> bool:
        return self.total_bookings_created >= self.daily_capacity

    def people_waiting(self) -> int:
        return len(self.waiting)

    def estimate_wait_minutes(self) -> int:
        # People ahead * average handling time.
        return len(self.waiting) * self.avg_service_minutes

    def create_booking(self, user_name: str) -> Optional[Booking]:
        if self.is_full():
            return None

        token = f"{self.service_id.upper()}-{self.next_token_number:03d}"
        estimated_wait = self.estimate_wait_minutes()
        booking = Booking(
            token=token,
            user_name=user_name,
            service_id=self.service_id,
            estimated_wait_minutes_at_booking=estimated_wait,
        )
        self.waiting.append(booking)
        self.total_bookings_created += 1
        self.next_token_number += 1
        return booking

    def mark_next_served(self) -> Optional[Booking]:
        if not self.waiting:
            return None
        served_booking = self.waiting.popleft()
        self.served_count += 1
        return served_booking


class VirtualQueueManager:
    """Orchestrates all service queues and provides admin/user operations."""

    def __init__(self, service_configs: List[Tuple[str, str, int, int]]):
        self.services: Dict[str, ServiceQueue] = {}
        for service_id, display_name, daily_capacity, avg_minutes in service_configs:
            self.services[service_id] = ServiceQueue(
                service_id=service_id,
                display_name=display_name,
                daily_capacity=daily_capacity,
                avg_service_minutes=avg_minutes,
            )

        # Optional support table to lookup booking details by token.
        self.booking_index: Dict[str, Booking] = {}

        # Queue length history for graphing: event_number -> per-service waiting counts.
        self.history: List[Dict[str, int]] = []
        self._record_history()

    def _record_history(self) -> None:
        snapshot = {sid: service.people_waiting() for sid, service in self.services.items()}
        self.history.append(snapshot)

    def list_services(self) -> List[ServiceQueue]:
        return list(self.services.values())

    def book_slot(self, user_name: str, service_id: str) -> Tuple[bool, str, Optional[Booking]]:
        service = self.services.get(service_id)
        if service is None:
            return False, f"Invalid service id: '{service_id}'.", None

        if not user_name.strip():
            return False, "User name cannot be empty.", None

        booking = service.create_booking(user_name=user_name.strip())
        if booking is None:
            return False, f"Service '{service.display_name}' is at full daily capacity.", None

        self.booking_index[booking.token] = booking
        self._record_history()
        return True, "Booking confirmed.", booking

    def mark_served(self, service_id: str) -> Tuple[bool, str, Optional[Booking]]:
        service = self.services.get(service_id)
        if service is None:
            return False, f"Invalid service id: '{service_id}'.", None

        served = service.mark_next_served()
        if served is None:
            return False, f"Queue is empty for service '{service.display_name}'.", None

        self._record_history()
        return True, f"Marked served: token {served.token} ({served.user_name}).", served

    def queue_status(self) -> List[Dict[str, int]]:
        status = []
        for service in self.services.values():
            status.append(
                {
                    "waiting": service.people_waiting(),
                    "served": service.served_count,
                    "booked_total": service.total_bookings_created,
                    "capacity": service.daily_capacity,
                    "avg_service_minutes": service.avg_service_minutes,
                    "est_wait_new_user": service.estimate_wait_minutes(),
                }
            )
        return status

    def queue_status_rows(self) -> List[str]:
        rows = []
        for s in self.services.values():
            rows.append(
                (
                    f"{s.service_id:<12} | waiting={s.people_waiting():<3} | served={s.served_count:<3} | "
                    f"booked={s.total_bookings_created:<3}/{s.daily_capacity:<3} | "
                    f"avg={s.avg_service_minutes}m | est_wait_new={s.estimate_wait_minutes()}m"
                )
            )
        return rows

    def print_history_graph(self) -> str:
        """
        Text graph of queue length over events.
        Each event is one successful booking or serve action.
        """
        lines: List[str] = ["Queue Length vs Event (ASCII graph)"]
        for service_id, service in self.services.items():
            lines.append(f"\n{service.display_name} [{service_id}]")
            for i, snapshot in enumerate(self.history):
                q_len = snapshot.get(service_id, 0)
                lines.append(f"event {i:02d}: {'#' * q_len} ({q_len})")
        return "\n".join(lines)


def print_menu() -> None:
    print("\n=== Virtual Queue Manager ===")
    print("1. List services")
    print("2. Book queue slot")
    print("3. Admin: Mark next user as served")
    print("4. Admin: View queue status")
    print("5. Optional: Show queue-length graph")
    print("6. Run demo scenario")
    print("0. Exit")


def ask_choice() -> str:
    return input("Select an option: ").strip()


def interactive_app() -> None:
    manager = VirtualQueueManager(
        service_configs=[
            ("cashier", "Cashier", 5, 4),
            ("doctor", "Doctor Consultation", 4, 12),
            ("consult", "General Consultation", 6, 8),
        ]
    )

    while True:
        print_menu()
        choice = ask_choice()

        if choice == "0":
            print("Exiting.")
            break

        if choice == "1":
            print("\nAvailable services:")
            for s in manager.list_services():
                print(
                    f"- id={s.service_id}, name={s.display_name}, "
                    f"daily_capacity={s.daily_capacity}, avg_service_time={s.avg_service_minutes}m"
                )

        elif choice == "2":
            user_name = input("Enter your name: ").strip()
            service_id = input("Enter service id: ").strip()
            ok, message, booking = manager.book_slot(user_name=user_name, service_id=service_id)
            print(message)
            if ok and booking:
                print(
                    f"Token: {booking.token} | Service: {booking.service_id} | "
                    f"Estimated wait: {booking.estimated_wait_minutes_at_booking} minutes"
                )

        elif choice == "3":
            service_id = input("Enter service id to serve next: ").strip()
            ok, message, _served = manager.mark_served(service_id=service_id)
            print(message)

        elif choice == "4":
            print("\nQueue status:")
            for row in manager.queue_status_rows():
                print(row)

        elif choice == "5":
            print(manager.print_history_graph())

        elif choice == "6":
            run_demo()

        else:
            print("Invalid option. Please enter a number from 0 to 6.")


def run_demo(manager: Optional[VirtualQueueManager] = None) -> None:
    """
    Deterministic example run to demonstrate behavior and edge cases.
    """
    local_manager = manager or VirtualQueueManager(
        service_configs=[
            ("cashier", "Cashier", 3, 5),
            ("doctor", "Doctor Consultation", 2, 10),
        ]
    )

    steps = [
        ("book", {"user_name": "Asha", "service_id": "doctor"}),
        ("book", {"user_name": "Ben", "service_id": "doctor"}),
        ("book", {"user_name": "Cara", "service_id": "doctor"}),  # capacity full edge case
        ("serve", {"service_id": "doctor"}),
        ("serve", {"service_id": "doctor"}),
        ("serve", {"service_id": "doctor"}),  # empty queue edge case
        ("book", {"user_name": "", "service_id": "cashier"}),  # invalid name edge case
        ("book", {"user_name": "Deep", "service_id": "unknown"}),  # invalid service edge case
    ]

    print("\n=== Demo Scenario ===")
    for action, payload in steps:
        if action == "book":
            ok, msg, booking = local_manager.book_slot(**payload)
            print(f"BOOK {payload} -> {msg}")
            if ok and booking:
                print(
                    f"  token={booking.token}, est_wait={booking.estimated_wait_minutes_at_booking}m, "
                    f"service={booking.service_id}"
                )
        elif action == "serve":
            ok, msg, _served = local_manager.mark_served(**payload)
            print(f"SERVE {payload} -> {msg}")

    print("\nFinal status:")
    for row in local_manager.queue_status_rows():
        print(row)
    print()
    print(local_manager.print_history_graph())


if __name__ == "__main__":
    interactive_app()
