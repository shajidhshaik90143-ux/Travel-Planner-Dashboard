from datetime import date, datetime, timedelta
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

from src.database import init_db, execute, seed_demo
from src.exports import dataframe_csv_bytes, excel_bytes, trip_pdf
from src.ui import inject_css, metric_cards

st.set_page_config(page_title="Travel Planner Dashboard", page_icon="✈️", layout="wide", initial_sidebar_state="expanded")
inject_css()
init_db()
seed_demo()

TRIP_TYPES = ["Leisure","Business","Adventure","Family","Solo","Honeymoon","Road Trip","Study"]
STATUSES = ["Planning","Booked","In Progress","Completed","Cancelled"]
ITINERARY_CATS = ["Sightseeing","Food","Transport","Hotel","Tour","Shopping","Activity","Meeting","Other"]
EXPENSE_CATS = ["Transport","Accommodation","Food","Tours","Shopping","Tickets","Insurance","Other"]
PACK_CATS = ["Clothing","Electronics","Documents","Health","Toiletries","Accessories","Essentials","Other"]

def qdf(sql, params=()):
    return pd.DataFrame([dict(r) for r in execute(sql, params, fetch=True)])

def get_trips():
    return qdf("SELECT * FROM trips ORDER BY start_date DESC, id DESC")

def selected_trip():
    trips = get_trips()
    if trips.empty:
        return None, trips
    ids = trips["id"].tolist()
    if st.session_state.get("trip_id") not in ids:
        st.session_state["trip_id"] = ids[0]
    row = trips[trips.id == st.session_state["trip_id"]].iloc[0].to_dict()
    return row, trips

def money(v, currency):
    return f"{currency} {v:,.2f}"

trip, trips = selected_trip()

with st.sidebar:
    st.markdown("## ✈️ Travel Planner")
    if not trips.empty:
        labels = {int(r.id): f"{r['name']} — {r['destination']}" for _, r in trips.iterrows()}
        current = st.session_state["trip_id"]
        choice = st.selectbox("Active trip", list(labels), index=list(labels).index(current), format_func=lambda x: labels[x])
        st.session_state["trip_id"] = choice
        trip, trips = selected_trip()
    st.divider()
    page = st.radio("Workspace", [
        "Overview","Itinerary","Budget & Expenses","Packing","Documents","Analytics","Export"
    ], index=0)
    st.divider()
    st.caption("Travel Planner Dashboard")
    st.caption("SQLite • Streamlit • Plotly")

if trip is None:
    st.error("No trip found. Create your first trip from the sidebar.")
    st.stop()

it_df = qdf("SELECT * FROM itinerary WHERE trip_id=? ORDER BY day_date,start_time", (trip["id"],))
ex_df = qdf("SELECT * FROM expenses WHERE trip_id=? ORDER BY expense_date DESC,id DESC", (trip["id"],))
pack_df = qdf("SELECT * FROM packing WHERE trip_id=? ORDER BY category,item", (trip["id"],))
doc_df = qdf("SELECT * FROM documents WHERE trip_id=? ORDER BY status,document", (trip["id"],))

start = pd.to_datetime(trip["start_date"]).date()
end = pd.to_datetime(trip["end_date"]).date()
days = max(1, (end - start).days + 1)
spent = float(ex_df["amount"].sum()) if not ex_df.empty else 0
planned = float(it_df["cost"].sum()) if not it_df.empty else 0
remaining = float(trip["budget"]) - spent
packed_count = int(pack_df["packed"].sum()) if not pack_df.empty else 0
pack_total = len(pack_df)
pack_pct = (packed_count / pack_total * 100) if pack_total else 0

st.markdown(f"""
<div class="hero">
<h1>✈️ {trip['name']}</h1>
<p>{trip['destination']} &nbsp;•&nbsp; {trip['start_date']} → {trip['end_date']} &nbsp;•&nbsp; {trip['travelers']} traveler(s) &nbsp;•&nbsp; {trip['status']}</p>
</div>
""", unsafe_allow_html=True)

if page == "Overview":
    metric_cards([
        ("Trip duration", f"{days} days", f"{start:%d %b %Y} → {end:%d %b %Y}"),
        ("Budget", money(trip["budget"], trip["currency"]), "Planned trip budget"),
        ("Spent", money(spent, trip["currency"]), f"{(spent/trip['budget']*100 if trip['budget'] else 0):.0f}% of budget"),
        ("Remaining", money(remaining, trip["currency"]), "Available budget"),
        ("Activities", str(len(it_df)), f"{len(it_df)} scheduled items"),
    ])
    st.markdown("### Trip setup")
    c1,c2,c3 = st.columns([1.4,1,1])
    with c1:
        st.info(f"**Destination:** {trip['destination']}\n\n**Trip type:** {trip['trip_type']}\n\n**Travelers:** {trip['travelers']}")
    with c2:
        st.metric("Planned itinerary cost", money(planned, trip["currency"]))
        st.metric("Packing progress", f"{pack_pct:.0f}%")
    with c3:
        ready = int((doc_df["status"]=="Ready").sum()) if not doc_df.empty else 0
        st.metric("Documents ready", f"{ready}/{len(doc_df)}")
        st.metric("Days until / since trip", str((start-date.today()).days))
    st.markdown("### Upcoming itinerary")
    upcoming = it_df.copy()
    if not upcoming.empty:
        upcoming["sort"] = pd.to_datetime(upcoming["day_date"] + " " + upcoming["start_time"])
        upcoming = upcoming.sort_values("sort").head(6).drop(columns="sort")
        st.dataframe(upcoming[["day_date","start_time","end_time","title","category","location","cost"]], use_container_width=True, hide_index=True)
    else:
        st.warning("No itinerary items yet. Add your first activity from the Itinerary page.")
    if trip["notes"]:
        st.markdown("### Trip notes")
        st.write(trip["notes"])

elif page == "Itinerary":
    st.markdown("### Day-by-day itinerary")
    with st.expander("➕ Add itinerary item", expanded=not bool(it_df)):
        with st.form("add_itinerary"):
            a,b,c = st.columns(3)
            with a:
                day_date = st.date_input("Date", value=start, min_value=start, max_value=end)
                title = st.text_input("Activity title", placeholder="e.g. Museum visit")
                category = st.selectbox("Category", ITINERARY_CATS)
            with b:
                start_time = st.time_input("Start time", value=datetime.strptime("09:00","%H:%M").time())
                end_time = st.time_input("End time", value=datetime.strptime("10:30","%H:%M").time())
                location = st.text_input("Location")
            with c:
                cost = st.number_input(f"Cost ({trip['currency']})", min_value=0.0, step=100.0)
                notes = st.text_area("Notes")
            if st.form_submit_button("Add to itinerary", type="primary"):
                execute("""INSERT INTO itinerary(trip_id,day_date,start_time,end_time,title,category,location,cost,notes)
                           VALUES(?,?,?,?,?,?,?,?,?)""",
                        (trip["id"],str(day_date),str(start_time),str(end_time),title,category,location,cost,notes))
                st.rerun()
    search = st.text_input("Search activities", placeholder="Search title, location or category...")
    view = it_df.copy()
    if search and not view.empty:
        mask = view.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        view = view[mask]
    if not view.empty:
        for day, group in view.groupby("day_date"):
            st.markdown(f"#### {pd.to_datetime(day).strftime('%A, %d %B %Y')}")
            for _, r in group.iterrows():
                c1,c2,c3,c4,c5 = st.columns([1.2,2.7,1.2,1.4,.7])
                c1.write(f"**{r['start_time']}**\n{r['end_time']}")
                c2.write(f"**{r['title']}**\n\n{r['location'] or 'Location not set'}")
                c3.write(r["category"])
                c4.write(money(r["cost"], trip["currency"]))
                if c5.button("🗑️", key=f"del_it_{r['id']}"):
                    execute("DELETE FROM itinerary WHERE id=?", (int(r["id"]),))
                    st.rerun()
    else:
        st.info("No matching itinerary items.")

elif page == "Budget & Expenses":
    st.markdown("### Budget & expenses")
    metric_cards([
        ("Trip budget", money(trip["budget"], trip["currency"]), "Overall target"),
        ("Recorded spend", money(spent, trip["currency"]), "All expense entries"),
        ("Itinerary estimate", money(planned, trip["currency"]), "Planned activity costs"),
        ("Remaining", money(remaining, trip["currency"]), "Budget minus recorded spend"),
    ])
    with st.expander("➕ Add expense", expanded=True):
        with st.form("add_expense"):
            a,b,c = st.columns(3)
            with a:
                edate = st.date_input("Expense date", value=date.today())
                ecat = st.selectbox("Category", EXPENSE_CATS)
            with b:
                desc = st.text_input("Description")
                amount = st.number_input(f"Amount ({trip['currency']})", min_value=0.0, step=100.0)
            with c:
                paid = st.checkbox("Paid", value=True)
            if st.form_submit_button("Add expense", type="primary"):
                execute("""INSERT INTO expenses(trip_id,expense_date,category,description,amount,paid)
                           VALUES(?,?,?,?,?,?)""", (trip["id"],str(edate),ecat,desc,amount,int(paid)))
                st.rerun()
    if not ex_df.empty:
        c1,c2 = st.columns(2)
        with c1:
            cat = ex_df.groupby("category", as_index=False)["amount"].sum()
            fig = px.pie(cat, names="category", values="amount", hole=.5, title="Spend by category")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            daily = ex_df.groupby("expense_date", as_index=False)["amount"].sum()
            fig = px.bar(daily, x="expense_date", y="amount", title="Daily spending", labels={"amount":f"Amount ({trip['currency']})"})
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(ex_df[["expense_date","category","description","amount","paid"]], use_container_width=True, hide_index=True)
        st.markdown("#### Delete expense")
        del_id = st.selectbox("Select expense", ex_df["id"].tolist(), format_func=lambda x: ex_df.loc[ex_df.id==x,"description"].iloc[0])
        if st.button("Delete selected expense"):
            execute("DELETE FROM expenses WHERE id=?", (int(del_id),))
            st.rerun()
    else:
        st.info("No expenses recorded yet.")

elif page == "Packing":
    st.markdown("### Packing checklist")
    st.progress(pack_pct/100, text=f"{packed_count} of {pack_total} items packed ({pack_pct:.0f}%)")
    with st.expander("➕ Add packing item"):
        with st.form("add_pack"):
            item = st.text_input("Item", placeholder="e.g. Rain jacket")
            cat = st.selectbox("Category", PACK_CATS)
            if st.form_submit_button("Add item", type="primary"):
                execute("INSERT INTO packing(trip_id,item,category,packed) VALUES(?,?,?,0)", (trip["id"],item,cat))
                st.rerun()
    if not pack_df.empty:
        for cat, group in pack_df.groupby("category"):
            st.markdown(f"#### {cat}")
            for _, r in group.iterrows():
                cols = st.columns([.08,1,.2])
                checked = cols[0].checkbox("", value=bool(r["packed"]), key=f"pack_{r['id']}")
                if checked != bool(r["packed"]):
                    execute("UPDATE packing SET packed=? WHERE id=?", (int(checked),int(r["id"])))
                    st.rerun()
                cols[1].write(r["item"])
                if cols[2].button("Remove", key=f"remove_pack_{r['id']}"):
                    execute("DELETE FROM packing WHERE id=?", (int(r["id"]),))
                    st.rerun()
    else:
        st.info("Your packing list is empty.")

elif page == "Documents":
    st.markdown("### Travel documents")
    with st.expander("➕ Add document"):
        with st.form("add_doc"):
            doc = st.text_input("Document name", placeholder="e.g. Visa")
            status = st.selectbox("Status", ["Pending","Ready","Not Required"])
            notes = st.text_input("Notes")
            if st.form_submit_button("Add document", type="primary"):
                execute("INSERT INTO documents(trip_id,document,status,notes) VALUES(?,?,?,?)",
                        (trip["id"],doc,status,notes))
                st.rerun()
    if not doc_df.empty:
        for _, r in doc_df.iterrows():
            a,b,c,d = st.columns([2.2,1.2,3,.7])
            a.write(f"**{r['document']}**")
            new_status = b.selectbox("Status",["Pending","Ready","Not Required"],index=["Pending","Ready","Not Required"].index(r["status"]),key=f"docstatus_{r['id']}",label_visibility="collapsed")
            if new_status != r["status"]:
                execute("UPDATE documents SET status=? WHERE id=?", (new_status,int(r["id"])))
                st.rerun()
            c.write(r["notes"] or "—")
            if d.button("🗑️",key=f"deldoc_{r['id']}"):
                execute("DELETE FROM documents WHERE id=?", (int(r["id"]),))
                st.rerun()
    else:
        st.info("No documents added.")

elif page == "Analytics":
    st.markdown("### Trip analytics")
    if not ex_df.empty:
        left,right = st.columns(2)
        with left:
            cat = ex_df.groupby("category", as_index=False)["amount"].sum()
            st.plotly_chart(px.bar(cat, x="category", y="amount", title="Expense categories", text_auto=".2s"), use_container_width=True)
        with right:
            daily = ex_df.groupby("expense_date", as_index=False)["amount"].sum()
            st.plotly_chart(px.line(daily, x="expense_date", y="amount", markers=True, title="Spending trend"), use_container_width=True)
    if not it_df.empty:
        act = it_df.groupby("category", as_index=False).agg(Activities=("id","count"), Cost=("cost","sum"))
        st.plotly_chart(px.bar(act, x="category", y="Activities", title="Activities by category"), use_container_width=True)
    c1,c2 = st.columns(2)
    with c1:
        st.metric("Average daily spend", money(spent/days, trip["currency"]))
        st.metric("Average activity cost", money(planned/len(it_df), trip["currency"]) if len(it_df) else money(0,trip["currency"]))
    with c2:
        st.metric("Spend per traveler", money(spent/max(1,trip["travelers"]), trip["currency"]))
        st.metric("Activities per day", f"{len(it_df)/days:.1f}")

elif page == "Export":
    st.markdown("### Export & trip management")
    st.write("Download your trip data for sharing, backup, or printing.")
    data = {
        "Itinerary": it_df,
        "Expenses": ex_df,
        "Packing": pack_df,
        "Documents": doc_df,
    }
    c1,c2,c3 = st.columns(3)
    with c1:
        st.download_button("⬇️ Itinerary CSV", dataframe_csv_bytes(it_df), "itinerary.csv", "text/csv", use_container_width=True)
    with c2:
        st.download_button("⬇️ Expenses CSV", dataframe_csv_bytes(ex_df), "expenses.csv", "text/csv", use_container_width=True)
    with c3:
        st.download_button("⬇️ Full Excel workbook", excel_bytes(data), "travel_plan.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    pdf = trip_pdf(trip,it_df,ex_df,pack_df,doc_df)
    st.download_button("📄 Download printable PDF", pdf, "travel_plan_summary.pdf", "application/pdf", use_container_width=True)
    st.divider()
    st.markdown("### Create a new trip")
    with st.form("new_trip"):
        a,b,c = st.columns(3)
        with a:
            name = st.text_input("Trip name")
            destination = st.text_input("Destination")
            sdate = st.date_input("Start date", value=date.today())
            edate = st.date_input("End date", value=date.today()+timedelta(days=4))
        with b:
            travelers = st.number_input("Travelers",1,50,1)
            trip_type = st.selectbox("Trip type",TRIP_TYPES)
            status = st.selectbox("Status",STATUSES)
            currency = st.text_input("Currency", value="USD", max_chars=5).upper()
        with c:
            budget = st.number_input("Budget", min_value=0.0, step=500.0)
            notes = st.text_area("Notes")
        if st.form_submit_button("Create trip", type="primary"):
            if not name.strip() or not destination.strip():
                st.error("Trip name and destination are required.")
            elif edate < sdate:
                st.error("End date cannot be before start date.")
            else:
                new_id = execute("""INSERT INTO trips(name,destination,start_date,end_date,travelers,trip_type,status,currency,budget,notes,created_at)
                                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                                 (name.strip(),destination.strip(),str(sdate),str(edate),int(travelers),trip_type,status,currency,budget,notes,datetime.now().isoformat(timespec="seconds")))
                st.session_state["trip_id"] = new_id
                st.success("Trip created.")
                st.rerun()
    st.divider()
    st.markdown("### Update active trip")
    with st.form("update_trip"):
        a,b,c = st.columns(3)
        with a:
            u_name = st.text_input("Name", value=trip["name"])
            u_dest = st.text_input("Destination", value=trip["destination"])
            u_budget = st.number_input("Budget", min_value=0.0, value=float(trip["budget"]), step=500.0)
        with b:
            u_start = st.date_input("Start", value=start)
            u_end = st.date_input("End", value=end)
            u_status = st.selectbox("Status", STATUSES, index=STATUSES.index(trip["status"]))
        with c:
            u_travelers = st.number_input("Travelers",1,50,int(trip["travelers"]))
            u_type = st.selectbox("Trip type",TRIP_TYPES,index=TRIP_TYPES.index(trip["trip_type"]))
            u_notes = st.text_area("Notes", value=trip["notes"])
        if st.form_submit_button("Save trip changes"):
            if u_end < u_start:
                st.error("End date cannot be before start date.")
            else:
                execute("""UPDATE trips SET name=?,destination=?,start_date=?,end_date=?,travelers=?,trip_type=?,status=?,budget=?,notes=? WHERE id=?""",
                        (u_name.strip(),u_dest.strip(),str(u_start),str(u_end),int(u_travelers),u_type,u_status,u_budget,u_notes,int(trip["id"])))
                st.success("Trip updated.")
                st.rerun()
    st.divider()
    if len(trips) > 1:
        st.markdown("### Delete active trip")
        st.warning("Deleting a trip also deletes its itinerary, expenses, packing list and documents.")
        confirm = st.checkbox("I understand and want to delete this trip.")
        if st.button("Delete active trip", type="secondary", disabled=not confirm):
            execute("DELETE FROM trips WHERE id=?", (int(trip["id"]),))
            st.session_state.pop("trip_id",None)
            st.rerun()
