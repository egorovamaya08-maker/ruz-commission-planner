import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time

st.set_page_config(page_title="RUZ Planner", layout="wide")
st.title("📅 RUZ Planner")
st.markdown("**Планирование комиссий и поиск свободных окон • СПбГТУ**")

# ========================= СЛОВАРЬ ГРУПП =========================
GROUP_MAP = {
    "3733801/50001": "41846",
    "3733801/50002": "41847",
    "3733801/50003": "41848",
    "3733801/50004": "41849",
    # Добавляй новые группы сюда:
    # "3733801/XXXXX": "XXXXX",
}

# ========================= ПАРСЕР ГРУПП (на базе твоего оригинального кода) =========================
def parse_group_schedule(group_human: str, start_date: datetime, end_date: datetime):
    if group_human not in GROUP_MAP:
        st.error(f"Группа {group_human} не найдена в словаре.")
        return pd.DataFrame()

    group_id = GROUP_MAP[group_human]
    all_lessons = []

    st.info(f"Начинаем парсинг группы **{group_human}** (ID: {group_id})")

    # Генерируем понедельники
    current = start_date - timedelta(days=start_date.weekday())
    progress_bar = st.progress(0)
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 2

    while current <= end_date:
        week_count += 1
        url = f"https://ruz.spbstu.ru/faculty/100/groups/{group_id}?date={current.strftime('%Y-%m-%d')}"

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                schedule_days = soup.find_all('li', class_='schedule__day')

                for day in schedule_days:
                    date_element = day.find('div', class_='schedule__date')
                    if not date_element:
                        continue
                    date_text = date_element.text.strip()

                    lesson_items = day.find_all('li', class_='lesson')

                    for lesson in lesson_items:
                        # Тип занятия
                        type_elem = lesson.find('div', class_='lesson__type')
                        lesson_type = type_elem.text.strip() if type_elem else "Неизвестно"

                        # Дисциплина
                        subject_elem = lesson.find('div', class_='lesson__subject')
                        subject = ""
                        if subject_elem:
                            spans = subject_elem.find_all('span')
                            if spans and len(spans) > 2:
                                subject = spans[-1].text.strip()

                        # Преподаватели
                        teachers = []
                        teachers_elem = lesson.find('div', class_='lesson__teachers')
                        if teachers_elem:
                            for a in teachers_elem.find_all('a'):
                                name = a.text.strip()
                                if name and len(name) > 3:
                                    teachers.append(name)

                        # Время
                        time_elem = lesson.find('span', class_='lesson__time')
                        lesson_time = time_elem.text.strip() if time_elem else ""

                        # Добавляем только если есть дисциплина и преподаватель
                        if subject and teachers:
                            all_lessons.append({
                                "date": date_text,
                                "group_human": group_human,
                                "discipline": subject,
                                "lesson_type": lesson_type,
                                "teachers": ", ".join(teachers),
                                "time": lesson_time
                            })

            progress_bar.progress(min(week_count / total_weeks, 1.0))
            time.sleep(10)  # пауза

        except Exception as e:
            st.warning(f"Ошибка на неделе {current.strftime('%Y-%m-%d')}: {e}")

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

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", datetime(2026, 2, 1))
    with col2:
        end_date = st.date_input("Дата окончания", datetime(2026, 5, 25))

    group_options = list(GROUP_MAP.keys())
    group_human = st.selectbox("Выберите группу", group_options)

    if st.button("🚀 Запустить парсинг расписания", type="primary"):
        with st.spinner("Парсинг расписания..."):
            df = parse_group_schedule(group_human, start_date, end_date)

            if not df.empty:
                st.session_state.schedule_df = df
                st.success(f"✅ Загружено {len(df)} занятий для группы {group_human}")
                st.dataframe(df)
            else:
                st.warning("Занятий не найдено или произошла ошибка")

with tab2:
    st.subheader("🔍 Поиск свободных окон")
    if "schedule_df" in st.session_state and not st.session_state.schedule_df.empty:
        st.success("Данные загружены. Поиск свободных окон будет добавлен дальше.")
    else:
        st.warning("Сначала загрузите расписание")

with tab3:
    st.subheader("📅 Планирование комиссий")
    st.info("Эта функция будет доступна после доработки парсера.")

with tab4:
    st.subheader("📊 Статистика")
    if "schedule_df" in st.session_state and not st.session_state.schedule_df.empty:
        df = st.session_state.schedule_df
        st.metric("Всего занятий", len(df))
        st.dataframe(df)
    else:
        st.info("Загрузите расписание")

st.caption("Версия 0.5 • Парсер групп улучшен")
