"""
Streamlit UI for the Virtual Queue Manager.

Run:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import streamlit as st

from virtual_queue_manager import VirtualQueueManager


DEFAULT_SERVICE_CONFIGS = [
    ("cashier", "Cashier", 20, 4),
    ("doctor", "Doctor Consultation", 15, 12),
    ("consult", "General Consultation", 25, 8),
]


def init_manager() -> None:
    if "manager" not in st.session_state:
        st.session_state.manager = VirtualQueueManager(service_configs=DEFAULT_SERVICE_CONFIGS)


def reset_manager() -> None:
    st.session_state.manager = VirtualQueueManager(service_configs=DEFAULT_SERVICE_CONFIGS)


def service_options(manager: VirtualQueueManager) -> dict[str, str]:
    return {s.display_name: s.service_id for s in manager.list_services()}


def render_status_table(manager: VirtualQueueManager) -> None:
    rows = []
    for s in manager.list_services():
        rows.append(
            {
                "service_id": s.service_id,
                "service_name": s.display_name,
                "waiting": s.people_waiting(),
                "served": s.served_count,
                "booked_total": s.total_bookings_created,
                "capacity": s.daily_capacity,
                "avg_service_minutes": s.avg_service_minutes,
                "est_wait_for_new_user": s.estimate_wait_minutes(),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Virtual Queue Manager", page_icon=":material/queue:", layout="wide")
    init_manager()
    manager: VirtualQueueManager = st.session_state.manager

    st.title("Virtual Queue Manager")
    st.caption("Online queue-slot booking simulation to reduce physical crowding.")

    with st.sidebar:
        st.subheader("System Controls")
        if st.button("Reset Day / Clear All Queues", type="secondary", use_container_width=True):
            reset_manager()
            st.success("Queues and counters reset.")
            st.rerun()

        st.markdown("### Service Capacity")
        for svc in manager.list_services():
            st.write(f"- {svc.display_name}: {svc.total_bookings_created}/{svc.daily_capacity} booked")

    left, right = st.columns(2)

    with left:
        st.subheader("User Booking")
        name = st.text_input("User name", placeholder="Enter user name")
        options = service_options(manager)
        selected_label = st.selectbox("Service type", list(options.keys()))
        if st.button("Book Virtual Slot", type="primary", use_container_width=True):
            ok, message, booking = manager.book_slot(user_name=name, service_id=options[selected_label])
            if ok and booking:
                st.success(
                    f"{message} Token: {booking.token} | "
                    f"Estimated wait: {booking.estimated_wait_minutes_at_booking} minutes."
                )
            else:
                st.error(message)

    with right:
        st.subheader("Admin / Staff Actions")
        options = service_options(manager)
        serve_label = st.selectbox("Service queue to serve", list(options.keys()), key="serve_service")
        if st.button("Mark Next User as Served", use_container_width=True):
            ok, message, _served = manager.mark_served(service_id=options[serve_label])
            if ok:
                st.success(message)
            else:
                st.warning(message)

    st.divider()
    st.subheader("Current Queue Status")
    render_status_table(manager)

    show_graph = st.toggle("Show queue length vs time graph (ASCII)")
    if show_graph:
        st.code(manager.print_history_graph(), language="text")

    st.info(
        "No SMS/real-time sync/payment integration is included. "
        "This is a local simulation app using in-memory state."
    )


if __name__ == "__main__":
    main()
