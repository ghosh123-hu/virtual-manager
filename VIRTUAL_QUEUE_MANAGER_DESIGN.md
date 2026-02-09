# Virtual Queue Manager - Design Notes

## 1) Confirmed Facts
- No backend is provided.
- Python-only logic/simulation is required.
- No real external integrations (real-time DB, SMS API, payment gateway) should be assumed.
- Required features: per-service queues, booking, token assignment, estimated wait, mark-as-served, queue status, capacity protection.

## 2) Assumptions
- Capacity is per service per day (total accepted bookings, including already served users).
- Estimated wait time is computed as:
  - `people_currently_waiting * average_service_time_for_that_service`
- Single process simulation (no concurrent writers).

## 3) Design Decisions
- `dict[str, ServiceQueue]` for service lookup by id:
  - Fast average O(1) access for booking/serving/status.
- `collections.deque` for each service waiting line:
  - O(1) append for booking and O(1) popleft for serving.
- `dataclass Booking` for token/user/service snapshot:
  - Keeps booking records structured and explicit.
- `history: list[dict[str, int]]` snapshots:
  - Enables optional queue-length-vs-event graph (ASCII).

## 4) System Architecture (Simple)
- User flow:
  1. User selects service id.
  2. System checks capacity for that service.
  3. System generates token and computes estimated wait.
  4. Booking is appended to that service queue.
- Admin flow:
  1. Staff selects service id.
  2. System pops the front token from that service queue.
  3. Status counters update (served/waiting/booked).
- Reporting:
  - Service-wise queue status table.
  - Optional ASCII graph from recorded queue snapshots.

## 5) Time Complexity (Main Operations)
- Book slot (`book_slot`):
  - Service lookup O(1), capacity check O(1), enqueue O(1).
  - Total: O(1).
- Mark served (`mark_served`):
  - Service lookup O(1), dequeue O(1).
  - Total: O(1).
- View status (`queue_status_rows`):
  - Iterates over number of services `S`.
  - Total: O(S).
- Print history graph:
  - Iterates over services `S` and events `E`.
  - Total: O(S * E).

## 6) Edge Cases Covered
- Invalid service id.
- Empty user name.
- Booking when service is at full daily capacity.
- Mark served when queue is empty.
- Invalid menu option.

## 7) File Implemented
- `/Users/atharvgautamghosh/Documents/physics 2/virtual_queue_manager.py`

## 8) Example Run (from demo mode)
```text
BOOK {'user_name': 'Asha', 'service_id': 'doctor'} -> Booking confirmed.
  token=DOCTOR-001, est_wait=0m, service=doctor
BOOK {'user_name': 'Ben', 'service_id': 'doctor'} -> Booking confirmed.
  token=DOCTOR-002, est_wait=10m, service=doctor
BOOK {'user_name': 'Cara', 'service_id': 'doctor'} -> Service 'Doctor Consultation' is at full daily capacity.
SERVE {'service_id': 'doctor'} -> Marked served: token DOCTOR-001 (Asha).
SERVE {'service_id': 'doctor'} -> Marked served: token DOCTOR-002 (Ben).
SERVE {'service_id': 'doctor'} -> Queue is empty for service 'Doctor Consultation'.
BOOK {'user_name': '', 'service_id': 'cashier'} -> User name cannot be empty.
BOOK {'user_name': 'Deep', 'service_id': 'unknown'} -> Invalid service id: 'unknown'.
```

## 9) Explicit Non-Implemented External Features
- Real online notifications (SMS/push/email), cross-device real-time sync, and production-grade multi-user consistency are not included.
- This cannot be implemented without external services.
