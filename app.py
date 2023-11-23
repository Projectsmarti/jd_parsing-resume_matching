import streamlit as st
import pandas as pd
import os
import re
import ast
import google.generativeai as palm
from fuzzywuzzy import fuzz

def hybrid_similarity(jd_skills, resume_skills, threshold):
    set1 = set(jd_skills)
    set2 = set(resume_skills)

    intersection_size = len(set1.intersection(set2))
    not_matched = set1 - set2

    if not_matched:
        mtchd_after_lvn = []
        for nm_skills in not_matched:
            for rsm_skills in resume_skills:
                leven_metric = fuzz.ratio(nm_skills, rsm_skills)
                if leven_metric >= threshold:
                    mtchd_after_lvn.append(nm_skills)

        intersection_size = intersection_size + len(mtchd_after_lvn)
        left_over_skills = set(not_matched) - set(mtchd_after_lvn)

        if left_over_skills:
            final_skl_mtch = []
            for skl in left_over_skills:
                for rsm_skl in resume_skills:
                    if skl in rsm_skl:
                        final_skl_mtch.append(skl)

            intersection_size = intersection_size + len(final_skl_mtch)

    union_size = len(set1)
    if union_size == 0:
        return 0

    return intersection_size / union_size

def extract_between_chars_regex(input_string, start_char, end_char):
    pattern = re.compile(f'{re.escape(start_char)}(.*?){re.escape(end_char)}')
    match = pattern.search(input_string)

    if match:
        return match.group(1)
    else:
        return None

def jd_skills_data_prep(text):
    skills = str(text).lower()
    skills = extract_between_chars_regex(skills, '[', ']')
    skills = skills.replace('"', '').replace("'", "").replace(")", "").replace(" and", ", ").replace("&", ", ")
    skills = skills.split(", ")
    return skills

def get_palm_response(text, prompt):
    os.environ['GOOGLE_API_KEY'] = 'AIzaSyCmdhOVj_KcpTxpWXH94DJOnBuXfZGZffg'
    palm.configure(api_key=os.environ['GOOGLE_API_KEY'])
    response = palm.generate_text(prompt=text + prompt)
    return response.result

def get_jd_skills_and_exp(jd_text):
    prompt1 = " Return python list with skill names only picked from above text"
    prompt2 = " Return minimum experience in years number only"

    skills = get_palm_response(prompt1, jd_text)
    skills = skills.lower()

    try:
        skills = ast.literal_eval(skills)
    except:
        skills = jd_skills_data_prep(skills)

    experience = float(get_palm_response(prompt2, jd_text))

    return jd_text, skills, experience

st.set_page_config(
    page_title="JD Parsing App",
    page_icon="📑",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a Bug': 'https://www.extremelycoolapp.com/bug',
        'About': 'This is a header. This is an extremely cool app!'
    }
)

st.markdown("<h1 style='text-align: center; color: Blue'>JD & RESUME MATCHING MATRIX </h1>", unsafe_allow_html=True)

st.sidebar.title("Navigation")
selected_option = st.sidebar.radio("Select an Option", ["Extract JD"])

jd_skills = ""
jd_experience = ""
jd_full_text = ""
if selected_option == "Upload File":
    st.title('JD File')

    uploaded_file = st.file_uploader("Choose a job description file", type=['txt', 'csv', 'docx', 'pdf'])
    if uploaded_file is not None:
        data = pd.read_excel(uploaded_file)
        st.markdown("<h2 style='text-align: center; color: #3498db;'>Job Description</h2>", unsafe_allow_html=True)
        st.table(data[['Text']])

else:
    st.markdown("<h3 style='text-align: left; color: Red'>Paste your JD Here </h3>", unsafe_allow_html=True)

    jd_full_text = st.text_area('', height=200)

    if st.button("Extract Skills and Experience"):
        jd_full_text, jd_skills, jd_experience = get_jd_skills_and_exp(jd_full_text)
        st.write(f"SKILLS REQUIRED: {jd_skills}")
        st.write(f"EXPERIENCE REQUIRED: {jd_experience}")

    resume_data = pd.read_csv(r"Resume_Parsed_Sample_v4_with_exp.csv")

    if st.button("Matched Resumes"):
        jd_full_text, jd_skills, jd_experience = get_jd_skills_and_exp(jd_full_text)
        st.write(f"SKILLS REQUIRED: {jd_skills}")
        st.write(f"EXPERIENCE REQUIRED: {jd_experience}")

        threshold = 90
        final_list = []

        for j, res_row in resume_data.iterrows():
            jd_skill_similarity = hybrid_similarity(jd_skills, eval(res_row[3]), threshold)

            # Missing skills
            Missing_Skills = list(set(jd_skills) - set(eval(res_row[3])))

            # Calculate additional skills
            additional_skills = list(set(eval(res_row[3])) - set(jd_skills))

            # Calculate matched skills
            matched_skills = list(set(jd_skills) - set(Missing_Skills))

            final_list.append(
                [jd_skills, jd_experience, res_row[0], res_row[3], additional_skills, res_row[5], jd_skill_similarity,
                 matched_skills])

        final_data = pd.DataFrame(final_list, columns=['JD_Skills', 'JD_Experience',
                                                       'Sl.No', 'Required_Skills', 'Additional_skills',
                                                       'Experience', 'Skill_Similarity', 'Matched_Skills'
                                                       ])

        final_data['Experience_Tag'] = final_data[['JD_Experience', 'Experience']].apply(
            lambda x: 1 if x['Experience'] >= x['JD_Experience'] else 0, axis=1)

        final_data['Matching_Score'] = final_data[['Skill_Similarity', 'Experience_Tag']].apply(
            lambda x: (x['Skill_Similarity'] + x['Experience_Tag']) / 2, axis=1)

        final_data = final_data.sort_values(['Matching_Score'], ascending=[False]).reset_index(drop=True)
        final_data['Matching_Score'] = final_data['Matching_Score'].apply(lambda x: str(int(x * 100)) + '%')

        top_5_matches = final_data.head()
        top_5_matches = top_5_matches[
            ['Sl.No', 'Matching_Score', 'Experience', 'Matched_Skills', 'Additional_skills']]

        top_5_matches
