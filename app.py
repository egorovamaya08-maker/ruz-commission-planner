import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="RUZ Planner", layout="wide")
st.title("📅 RUZ Planner")
st.markdown("**Поиск свободных окон и планирование • СПбГТУ**")

# ========================= СЛОВАРИ =========================
GROUP_MAP = {
    "3733801/50001": "41846",
    "3733801/50002": "41847",
    "3733801/50003": "41848",
    "3733801/50004": "41849",
}

TEACHER_MAP = {
    "Зайцев Андрей Александрович": "19997",
    "Благова Ирина Юрьевна": "23640",
}

# ========================= ПАРСЕР ГРУПП =========================
def parse_group_schedule(group_human: str, start_date: datetime, end_date: datetime):
    if group_human not in GROUP_MAP:
        st.error(f"Группа {group_human} не найдена.")
        return pd.DataFrame()

    group_id = GROUP_MAP[group_human]
    all_lessons = []

    current = start_date - timedelta(days=start_date.weekday())
    progress_bar = st.progress(0)
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 2

    stop_parsing = st.button("⛔ Остановить парсинг", key="stop_group")

    while current <= end_date:
        if stop_parsing:
            st.warning("Парсинг остановлен пользователем.")
            break

        week_count += 1
        url = f"https://ruz.spbstu.ru/faculty/100/groups/{group_id}?date={current.strftime('%Y-%m-%d')}"

        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for day in soup.find_all('li', class_='schedule__day'):
                    date_elem = day.find('div', class_='schedule__date')
                    if not date_elem:
                        continue
                    date_text = date_elem.text.strip()

                    for lesson in day.find_all('li', class_='lesson'):
                        subject = ""
                        subject_elem = lesson.find('div', class_='lesson__subject')
                        if subject_elem:
                            spans = subject_elem.find_all('span')
                            if spans and len(spans) > 2:
                                subject = spans[-1].text.strip()

                        lesson_type = lesson.find('div', class_='lesson__type')
                        lesson_type = lesson_type.text.strip() if lesson_type else ""

                        teachers = []
                        teachers_elem = lesson.find('div', class_='lesson__teachers')
                        if teachers_elem:
                            for a in teachers_elem.find_all('a'):
                                name = a.text.strip()
                                if name and len(name) > 3:
                                    teachers.append(name)

                        time_str = lesson.find('span', class_='lesson__time')
                        time_str = time_str.text.strip() if time_str else ""

                        place_elem = lesson.find('div', class_='lesson__places')
                        place = ""
                        if place_elem:
                            link = place_elem.find('a', class_='lesson__link')
                            if link:
                                place = link.get_text(strip=True)

                        if subject and teachers:
                            all_lessons.append({
                                "Дата": date_text,
                                "Время": time_str,
                                "Дисциплина": subject,
                                "Тип занятия": lesson_type,
                                "Преподаватель": ", ".join(teachers),
                                "Место": place,
                                "Группа": group_human
                            })

            progress_bar.progress(min(week_count / total_weeks, 1.0))
            time.sleep(12)

        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {e}")

        current += timedelta(weeks=1)

    return pd.DataFrame(all_lessons)

# ========================= ИНТЕРФЕЙС =========================
tab1, tab2 = st.tabs(["📥 Обновление расписания", "🔍 Поиск свободных окон"])

with tab1:
    st.subheader("Загрузка расписания")

    mode = st.radio("Что парсим?", ["Группу", "Преподавателя"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", datetime(2026, 2, 1))
    with col2:
        end_date = st.date_input("Дата окончания", datetime(2026, 5, 25))

    if mode == "Группу":
        group_human = st.selectbox("Выберите группу", list(GROUP_MAP.keys()))
        if st.button("🚀 Запустить парсинг группы", type="primary"):
            with st.spinner("Парсинг..."):
                df = parse_group_schedule(group_human, start_date, end_date)
                if not df.empty:
                    st.session_state.schedule_df = df
                    st.success(f"✅ Загружено {len(df)} занятий")
                    # Разделение по дням
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        day_df = df[df['Дата'] == date]
                        st.dataframe(day_df[['Дата', 'Время', 'Дисциплина', 'Тип занятия', 'Преподаватель', 'Место']])
    else:
        st.info("Парсинг по преподавателю пока в разработке")

with tab2:
    st.subheader("🔍 Поиск свободных окон")
    
    if "schedule_df" in st.session_state and not st.session_state.schedule_df.empty:
        df = st.session_state.schedule_df
        st.success(f"Загружено {len(df)} занятий")

        min_duration = st.slider("Минимальная длительность свободного окна (мин)", 30, 180, 60)

        if st.button("🔎 Найти свободные окна"):
            st.info("Поиск свободных окон по загруженным данным (в разработке)")
            st.dataframe(df)
    else:
        st.warning("Сначала загрузите расписание на первой вкладке")

st.caption("Версия 0.8 • Результаты сохраняются между вкладками • Пауза 12 сек")
