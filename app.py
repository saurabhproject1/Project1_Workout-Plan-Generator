import os
import re
from io import BytesIO
from xml.sax.saxutils import escape

import streamlit as st
from dotenv import load_dotenv
from groq import Groq

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)


# ==========================================
# 1. LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")


# ==========================================
# 2. PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="AI Workout Plan Generator",
    page_icon="💪",
    layout="wide"
)


# ==========================================
# 3. APPLICATION HEADING
# ==========================================

st.title("💪 AI Workout Plan Generator")

st.write(
    "Generate a personalized workout plan "
    "based on your fitness goals using AI."
)

st.divider()


# ==========================================
# 4. INPUT VALIDATION FUNCTION
# ==========================================

def validate_inputs(
    fitness_goal: str,
    experience: str,
    days_per_week: int,
    equipment: str
) -> str | None:

    if not fitness_goal:
        return "Please select a fitness goal."

    if not experience:
        return "Please select your experience level."

    if not isinstance(days_per_week, int):
        return "Workout days must be a valid number."

    if days_per_week < 1 or days_per_week > 7:
        return "Workout days must be between 1 and 7."

    if not equipment:
        return "Please select your equipment."

    return None


# ==========================================
# 5. WORKOUT GENERATION FUNCTION
# ==========================================

def generate_workout_plan(
    fitness_goal: str,
    experience: str,
    days_per_week: int,
    equipment: str,
    injuries: str
) -> str:

    if not api_key:
        raise ValueError(
            "Groq API key not found. Please check your .env file."
        )

    try:

        client = Groq(api_key=api_key)

        # Build the prompt
        prompt = f"""
        Create a personalized weekly workout plan.

        USER PROFILE:

        Fitness Goal: {fitness_goal}
        Experience Level: {experience}
        Available Days Per Week: {days_per_week}
        Equipment Available: {equipment}
        Injuries or Limitations: {injuries}

        INSTRUCTIONS:

        1. Create a complete 7-day workout schedule.
        2. Respect the user's fitness goal.
        3. Adjust workout intensity according to experience.
        4. Use only the available equipment.
        5. Include exercises, sets and repetitions.
        6. Include rest periods between exercises.
        7. Include warm-up and cool-down instructions.
        8. Include appropriate recovery days.
        9. Distribute training across the available days.
        10. Do not recommend exercises that conflict
            with reported injuries or limitations.
        11. Do not make medical claims.
        12. If injuries or limitations are mentioned,
            include a safety disclaimer.
        13. Use clear headings and Markdown tables.
        14. Explain the purpose of each training day.

        IMPORTANT:

        Available workout days do not mean that the user
        must train intensely every day.

        Include suitable rest and recovery days.

        Do not diagnose or prescribe treatment for injuries.
        """

        # Call Groq API
        completion = client.chat.completions.create(

            model="openai/gpt-oss-120b",

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an experienced fitness trainer. "
                        "Create practical, safe and personalized "
                        "workout plans. Respect all user constraints."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.7,
            max_completion_tokens=4000
        )

        # Extract AI response
        response = completion.choices[0].message.content

        # Check empty response
        if not response or not response.strip():

            raise ValueError(
                "The AI returned an empty response. Please try again."
            )

        return response

    except ValueError:
        raise

    except Exception as e:

        raise RuntimeError(
            f"Unable to generate workout plan: {e}"
        ) from e


# ==========================================
# 6. PDF GENERATION FUNCTION
# ==========================================

def generate_pdf(workout_plan: str) -> bytes:

    buffer = BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=20,
        leading=25,
        textColor=colors.HexColor("#16324F"),
        alignment=TA_CENTER,
        spaceAfter=15
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#176B87"),
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
        spaceAfter=5
    )

    story = []

    story.append(
        Paragraph(
            "YOUR PERSONALIZED WORKOUT PLAN",
            title_style
        )
    )

    story.append(
        Paragraph(
            "Generated by AI Workout Plan Generator",
            body_style
        )
    )

    story.append(Spacer(1, 12))

    # Convert Markdown content into PDF elements
    lines = workout_plan.split("\n")

    index = 0

    while index < len(lines):

        line = lines[index].strip()

        if not line:
            story.append(Spacer(1, 5))
            index += 1
            continue

        # Handle Markdown tables
        if line.startswith("|"):

            table_data = []

            while index < len(lines):

                current_line = lines[index].strip()

                if not current_line.startswith("|"):
                    break

                cells = [
                    cell.strip()
                    for cell in current_line.strip("|").split("|")
                ]

                # Ignore Markdown separator rows
                if all(
                    re.fullmatch(r":?-{3,}:?", cell.replace(" ", ""))
                    for cell in cells
                ):
                    index += 1
                    continue

                row = [
                    Paragraph(escape(cell), body_style)
                    for cell in cells
                ]

                table_data.append(row)

                index += 1

            if table_data:

                column_count = max(
                    len(row) for row in table_data
                )

                table = Table(
                    table_data,
                    colWidths=[
                        (A4[0] - 36 * mm) / column_count
                    ] * column_count,
                    repeatRows=1
                )

                table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0),
                         colors.HexColor("#16324F")),

                        ("TEXTCOLOR", (0, 0), (-1, 0),
                         colors.white),

                        ("GRID", (0, 0), (-1, -1),
                         0.5, colors.grey),

                        ("VALIGN", (0, 0), (-1, -1), "TOP"),

                        ("PADDING", (0, 0), (-1, -1), 6),

                        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                         [colors.white,
                          colors.HexColor("#F1F4F7")])
                    ])
                )

                story.append(table)
                story.append(Spacer(1, 10))

            continue

        # Handle headings
        if line.startswith("#"):

            heading = line.lstrip("#").strip()

            story.append(
                Paragraph(
                    escape(heading),
                    heading_style
                )
            )

        # Handle bullet points
        elif line.startswith("- ") or line.startswith("* "):

            content = line[2:].strip()

            story.append(
                Paragraph(
                    "&#8226; " + escape(content),
                    body_style
                )
            )

        # Handle numbered lists
        elif re.match(r"^\d+\.\s", line):

            story.append(
                Paragraph(
                    escape(line),
                    body_style
                )
            )

        else:

            # Remove basic Markdown formatting
            clean_line = re.sub(
                r"\*\*(.*?)\*\*",
                r"\1",
                line
            )

            clean_line = re.sub(
                r"\*(.*?)\*",
                r"\1",
                clean_line
            )

            clean_line = re.sub(
                r"`(.*?)`",
                r"\1",
                clean_line
            )

            story.append(
                Paragraph(
                    escape(clean_line),
                    body_style
                )
            )

        index += 1

    # Page number
    def add_page_number(canvas, document):

        canvas.saveState()

        canvas.setFont("Helvetica", 8)

        canvas.setFillColor(colors.grey)

        canvas.drawRightString(
            A4[0] - 18 * mm,
            10 * mm,
            f"Page {document.page}"
        )

        canvas.restoreState()

    pdf.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number
    )

    buffer.seek(0)

    return buffer.getvalue()


# ==========================================
# 7. USER INPUT SECTION
# ==========================================

st.header("Tell us about yourself")

fitness_goal = st.selectbox(
    "What is your fitness goal?",
    [
        "Build Muscle",
        "Lose Fat",
        "General Fitness",
        "Improve Endurance"
    ]
)

experience = st.selectbox(
    "What is your experience level?",
    [
        "Beginner",
        "Intermediate",
        "Advanced"
    ]
)

days_per_week = st.slider(
    "How many days can you exercise per week?",
    min_value=1,
    max_value=7,
    value=4
)

equipment = st.selectbox(
    "What equipment do you have?",
    [
        "No Equipment",
        "Home Dumbbells",
        "Full Gym"
    ]
)

injuries = st.text_area(
    "Any injuries or physical limitations? (Optional)"
)


# ==========================================
# 8. GENERATE WORKOUT PLAN
# ==========================================

if st.button(
    "Generate Workout Plan",
    type="primary"
):

    # Validate user inputs
    validation_error = validate_inputs(
        fitness_goal,
        experience,
        days_per_week,
        equipment
    )

    if validation_error:

        st.warning(validation_error)

    elif not api_key:

        st.error(
            "Groq API key not found. "
            "Please check your .env file."
        )

    else:

        try:

            with st.spinner(
                "AI is creating your personalized workout plan..."
            ):

                result = generate_workout_plan(
                    fitness_goal=fitness_goal,
                    experience=experience,
                    days_per_week=days_per_week,
                    equipment=equipment,
                    injuries=(
                        injuries.strip()
                        if injuries.strip()
                        else "None"
                    )
                )

            # Store generated plan
            st.session_state["workout_plan"] = result

            st.success(
                "Your workout plan has been generated successfully!"
            )

        except ValueError as e:

            st.warning(str(e))

        except Exception as e:

            st.error(
                "Unable to generate your workout plan. "
                "Please check your API key, internet connection "
                "or Groq service and try again."
            )

            st.caption(f"Technical details: {e}")


# ==========================================
# 9. DISPLAY GENERATED WORKOUT PLAN
# ==========================================

if "workout_plan" in st.session_state:

    result = st.session_state["workout_plan"]

    st.divider()

    st.header("🏋️ Your Personalized Workout Plan")

    st.markdown(result)

    st.divider()

    st.subheader("Download Your Workout Plan")

    # Generate PDF
    try:

        pdf_file = generate_pdf(result)

        col1, col2 = st.columns(2)

        with col1:

            st.download_button(
                label="📄 Download PDF",
                data=pdf_file,
                file_name="my_workout_plan.pdf",
                mime="application/pdf",
                use_container_width=True
            )

        with col2:

            st.download_button(
                label="📝 Download Markdown",
                data=result,
                file_name="my_workout_plan.md",
                mime="text/markdown",
                use_container_width=True
            )

    except Exception as e:

        st.error(
            f"Unable to generate PDF: {e}"
        )
