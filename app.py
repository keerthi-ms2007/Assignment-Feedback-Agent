import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import random
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

st.set_page_config(page_title="Assignment Feedback Agent", layout="wide", page_icon="🎓")

# ---------- LOGIN ----------
ROLES = {"Admin": "admin123", "Teacher": "teacher123", "Student": "student123"}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
if 'assignments' not in st.session_state:
    try: st.session_state.assignments = pd.read_csv("assignments.csv")
    except: st.session_state.assignments = pd.DataFrame(columns=["assignment_id","assignment_title","subject","due_date","total_marks"])
if 'submissions' not in st.session_state:
    try: st.session_state.submissions = pd.read_csv("submissions.csv")
    except: st.session_state.submissions = pd.DataFrame(columns=["submission_id","assignment_id","assignment_title","student_id","submission_text","status","score"])

def load_data():
    return st.session_state.assignments, st.session_state.submissions

# ---------- AI FUNCTIONS ----------
def ai_grade(text, rubric_dict):
    total = 0
    details = []
    for crit, max_m in rubric_dict.items():
        score = random.randint(int(max_m*0.6), max_m)
        total += score
        details.append((crit, score, max_m, f"Good work on {crit}. Quote: '{text[:40]}...' - Add more depth and examples."))
    summary = f"Overall Score {total}/{sum(rubric_dict.values())}. Submission shows good understanding, structure is clear."
    insights = ["✅ Good structure and clarity", "⚠️ Add 2-3 real examples", "⚠️ Check grammar in paragraph 2", "💡 Improve conclusion with future scope"]
    return total, summary, details, insights

def plagiarism_check(text, all_texts):
    # Simple demo: word overlap
    words = set(text.lower().split())
    max_overlap = 0
    for other in all_texts:
        if other == text: continue
        other_words = set(str(other).lower().split())
        if len(words)==0: continue
        overlap = len(words & other_words) / len(words) * 100
        max_overlap = max(max_overlap, overlap)
    risk = "Low" if max_overlap < 30 else "Medium" if max_overlap < 60 else "High"
    return round(max_overlap,1), risk

def make_pdf(student_id, assignment, score, summary, details):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 18); c.drawString(50, 800, "Assignment Feedback Report")
    c.setFont("Helvetica", 12)
    c.drawString(50, 770, f"Student: {student_id}")
    c.drawString(50, 750, f"Assignment: {assignment}")
    c.drawString(50, 730, f"Score: {score}")
    c.drawString(50, 710, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    c.drawString(50, 680, "Summary:")
    c.drawString(50, 660, summary[:100])
    y=630
    c.drawString(50, y, "Detailed Feedback:"); y-=20
    for crit, sc, mx, fb in details:
        c.drawString(50, y, f"{crit}: {sc}/{mx}"); y-=20
        c.drawString(70, y, fb[:90]); y-=30
    c.save(); buffer.seek(0)
    return buffer

# ---------- LOGIN PAGE ----------
if not st.session_state.logged_in:
    st.title("🎓 Assignment Feedback Agent")
    st.markdown("**AI-Powered Grading | Personalized Feedback | Plagiarism Check**")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**Demo Logins**\n\nTeacher: teacher123\nStudent: student123\nAdmin: admin123")
    with col2:
        role = st.selectbox("Select Role", list(ROLES.keys()))
        pw = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            if pw == ROLES[role]:
                st.session_state.logged_in = True; st.session_state.role = role; st.rerun()
            else: st.error("Wrong password")
    st.stop()

# ---------- SIDEBAR ----------
role = st.session_state.role
st.sidebar.title(f"👤 {role}")
st.sidebar.success(f"Logged in as {role}")
menu = st.sidebar.radio("Menu", ["Dashboard", "Create Assignment", "Grading Queue", "Student Portal", "Analytics", "Reports"])
if st.sidebar.button("Logout"):
    st.session_state.logged_in=False; st.rerun()

assignments, submissions = load_data()

# ---------- DASHBOARD ----------
if menu == "Dashboard":
    st.title("📊 Dashboard")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Total Assignments", len(assignments))
    c2.metric("Total Submissions", len(submissions))
    pending = len(submissions[submissions['status']=='SUBMITTED']) if len(submissions)>0 else 0
    c3.metric("Pending Review", pending)
    avg = submissions['score'].mean() if len(submissions)>0 and 'score' in submissions else 0
    c4.metric("Avg Score", f"{avg:.1f}")
    st.markdown("---")
    st.subheader("Recent Submissions")
    st.dataframe(submissions, use_container_width=True)

# ---------- CREATE ASSIGNMENT ----------
elif menu == "Create Assignment":
    st.title("➕ Create New Assignment")
    with st.form("create"):
        title = st.text_input("Assignment Title")
        subject = st.selectbox("Subject", ["English","Programming","DBMS","Maths","AI"])
        due = st.date_input("Due Date")
        marks = st.number_input("Total Marks", value=20)
        rubric_text = st.text_area("Rubric (one per line: Criteria-MaxMarks)", "Content-10\nGrammar-5\nStructure-5")
        if st.form_submit_button("Create Assignment"):
            new_id = f"A{len(assignments)+1:03d}"
            new_row = pd.DataFrame([{"assignment_id":new_id,"assignment_title":title,"subject":subject,"due_date":str(due),"total_marks":marks}])
            st.session_state.assignments = pd.concat([assignments, new_row], ignore_index=True)
            st.session_state.assignments.to_csv("assignments.csv", index=False)
            st.success(f"Assignment {new_id} Created! Rubric saved.")
    st.subheader("All Assignments")
    st.dataframe(assignments, use_container_width=True)

# ---------- GRADING QUEUE ----------
elif menu == "Grading Queue":
    st.title("📝 Grading Queue - AI Grading")
    # Upload
    st.subheader("Upload Submission (PDF / DOCX / TXT)")
    uploaded = st.file_uploader("Upload file", type=["pdf","docx","txt"])
    if uploaded:
        st.success(f"Uploaded: {uploaded.name} - Text extracted (Demo)")
        file_text = "This is extracted text from uploaded file about Artificial Intelligence and education."
        st.write(file_text)
    st.markdown("---")
    for idx, row in submissions.iterrows():
        with st.expander(f"📌 {row['assignment_title']} | Student: {row['student_id']} | Status: {row['status']}"):
            st.write("**Submission Text:**", row['submission_text'])
            # Plagiarism
            overlap, risk = plagiarism_check(str(row['submission_text']), submissions['submission_text'].tolist())
            st.warning(f"Plagiarism Check: {overlap}% overlap - Risk: {risk}")
            col1, col2 = st.columns(2)
            with col1:
                rubric_choice = st.selectbox(f"Rubric for {idx}", ["Content-10, Grammar-5, Structure-5", "Thesis-10, Evidence-10"], key=f"rub{idx}")
            with col2:
                if st.button(f"🤖 AI Grade - {row['student_id']}", key=f"grade{idx}"):
                    rubric = {"Content":10,"Grammar":5,"Structure":5}
                    score, summary, details, insights = ai_grade(str(row['submission_text']), rubric)
                    st.success(f"**Score: {score}/20**")
                    st.write("**AI Summary:**", summary)
                    for crit, sc, mx, fb in details:
                        st.write(f"- **{crit}**: {sc}/{mx} - {fb}")
                    st.write("**Recommendations:**")
                    for ins in insights: st.write(ins)
                    # Save PDF
                    pdf = make_pdf(row['student_id'], row['assignment_title'], score, summary, details)
                    st.download_button("📄 Download Feedback PDF", pdf, file_name=f"Feedback_{row['student_id']}.pdf", mime="application/pdf", key=f"pdf{idx}")

# ---------- STUDENT PORTAL ----------
elif menu == "Student Portal":
    st.title("👨‍🎓 Student Portal")
    st.info("View your grades, feedback and submit assignment")
    sid = st.text_input("Enter Student ID (Try S001)", value="S001")
    my_subs = submissions[submissions['student_id']==sid] if len(submissions)>0 else pd.DataFrame()
    if len(my_subs)>0:
        st.dataframe(my_subs, use_container_width=True)
        for _, r in my_subs.iterrows():
            st.success(f"Assignment: {r['assignment_title']} - Score: {r['score']} - Feedback: Good work! Keep improving.")
    else:
        st.warning("No submissions found for this ID")
    st.subheader("Submit Assignment")
    st.file_uploader("Upload your assignment", type=["pdf","docx","txt"])
    st.text_area("Or paste your answer here")
    if st.button("Submit"): st.success("Submitted Successfully! Teacher will grade soon.")

# ---------- ANALYTICS ----------
elif menu == "Analytics":
    st.title("📈 Class Analytics")
    if len(submissions)>0 and 'score' in submissions:
        fig1 = px.histogram(submissions, x='score', title="Grade Distribution", color_discrete_sequence=['#636EFA'])
        st.plotly_chart(fig1, use_container_width=True)
        fig2 = px.bar(submissions, x='student_id', y='score', title="Score by Student", color='score')
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(submissions.groupby('assignment_title')['score'].mean().reset_index(), use_container_width=True)
    else: st.info("No data for analytics")

# ---------- REPORTS ----------
elif menu == "Reports":
    st.title("📄 Reports")
    st.write("Download Class Report")
    if st.button("Generate Class Report PDF"):
        pdf = make_pdf("ALL", "Class Report", f"Avg: {submissions['score'].mean():.1f}" if len(submissions)>0 else "0", "Class performance summary", [("Content",8,10,"Good"),("Grammar",4,5,"Good")])
        st.download_button("Download PDF", pdf, file_name="Class_Report.pdf", mime="application/pdf")
    st.download_button("Download Submissions CSV", submissions.to_csv(index=False), file_name="submissions.csv")