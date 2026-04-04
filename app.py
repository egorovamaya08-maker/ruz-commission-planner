import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="RUZ Planner", layout="wide")
st.title("📅 RUZ Planner")
st.markdown("**Планирование комиссий и поиск свободных окон • СПбГТУ**")

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
        st.error(f"Группа {group_human} не найдена в словаре.")
        return pd.DataFrame()

    group_id = GROUP_MAP[group_human]
    all_lessons = []

    current = start_date - timedelta(days=start_date.weekday())
    progress_bar = st.progress(0)
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 2

    while current <= end_date:
        week_count += 1
        url = f"https://ruz.spbstu.ru/faculty/100/groups/{group_id}?date={current.strftime('%Y-%m-%d')}"

        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                schedule_days = soup.find_all('li', class_='schedule__day')

                for day in schedule_days:
                    date_elem = day.find('div', class_='schedule__date')
                    if not date_elem:
                        continue
                    date_text = date_elem.text.strip()

                    for lesson in day.find_all('li', class_='lesson'):
                        # Дисциплина
                        subject = ""
                        subject_elem = lesson.find('div', class_='lesson__subject')
                        if subject_elem:
                            spans = subject_elem.find_all('span')
                            if spans and len(spans) > 2:
                                subject = spans[-1].text.strip()

                        # Тип занятия
                        lesson_type = ""
                        type_elem = lesson.find('div', class_='lesson__type')
                        if type_elem:
                            lesson_type = type_elem.text.strip()

                        # Преподаватели
                        teachers = []
                        teachers_elem = lesson.find('div', class_='lesson__teachers')
                        if teachers_elem:
                            for a in teachers_elem.find_all('a'):
                                name = a.text.strip()
                                if name and len(name) > 3:
                                    teachers.append(name)

                        # Время
                        time_str = ""
                        time_elem = lesson.find('span', class_='lesson__time')
                        if time_elem:
                            time_str = time_elem.text.strip()

                        # Место (аудитория + корпус)
                        place = ""
                        place_elem = lesson.find('div', class_='lesson-places__list')
                        if place_elem:
                            place = place_elem.get_text(strip=True)

                        if subject and teachers:
                            all_lessons.append({
                                "date": date_text,
                                "group_human": group_human,
                                "discipline": subject,
                                "lesson_type": lesson_type,
                                "teachers": ", ".join(teachers),
                                "time": time_str,
                                "place": place
                            })

            progress_bar.progress(min(week_count / total_weeks, 1.0))
            time.sleep(12)  # пауза 12 секунд — безопасно

        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {e}")

        current += timedelta(weeks=1)

    return pd.DataFrame(all_lessons)

# ========================= ИНТЕРФЕЙС =========================
tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Обновление расписания", 
    "🔍 Поиск свободных окон", 
    "📅 Планирование комиссий", 
    "📊 Статистика"
])

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
                    st.success(f"Загружено {len(df)} занятий")
                    st.dataframe(df)
    else:
        st.info("Парсинг по преподавателю будет добавлен на следующем шаге")

with tab2:
    st.subheader("🔍 Поиск свободных окон")
    if "schedule_df" in st.session_state and not st.session_state.schedule_df.empty:
        st.dataframe(st.session_state.schedule_df)
        min_duration = st.slider("Мин. длительность окна (мин)", 60, 180, 90)
        if st.button("Найти свободные окна"):
            st.info("Поиск пока в разработке")
    else:
        st.warning("Сначала загрузите расписание")

with tab3:
    st.subheader("📅 Планирование комиссий")
    st.info("Будет добавлено позже")

with tab4:
    st.subheader("📊 Статистика")
    if "schedule_df" in st.session_state and not st.session_state.schedule_df.empty:
        df = st.session_state.schedule_df
        st.metric("Всего занятий", len(df))
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("По типам занятий:")
            st.dataframe(df['lesson_type'].value_counts())
        with col2:
            st.write("По преподавателям:")
            st.dataframe(df['teachers'].value_counts())
    else:
        st.info("Загрузите расписание")

st.caption("Версия 0.6 • Парсер групп улучшен • Пауза 12 сек")
