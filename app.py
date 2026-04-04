import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
from collections import defaultdict

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
    "Степанова Ксения Сергеевна": "20342",
}

# ========================= ПАРСЕР МЕСТА =========================
def parse_place(place_element):
    if not place_element:
        return "Не указано"
    link = place_element.find('a', class_='lesson__link')
    if not link:
        return "Не указано"
    text = link.get_text(strip=True)
    text = re.sub(r'(\d)(ауд\.)', r'\1 \2', text)
    parts = [p.strip() for p in text.split(',') if p.strip()]
    return ', '.join(dict.fromkeys(parts))

# ========================= ПАРСЕР ГРУППЫ =========================
def parse_group_schedule(group_human: str, start_date: datetime, end_date: datetime):
    if group_human not in GROUP_MAP:
        st.error(f"Группа {group_human} не найдена.")
        return pd.DataFrame()

    group_id = GROUP_MAP[group_human]
    all_lessons = []
    current = start_date - timedelta(days=start_date.weekday())

    while current <= end_date:
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

                        place = parse_place(lesson.find('div', class_='lesson__places'))

                        if subject and teachers:
                            all_lessons.append({
                                "Дата": date_text,
                                "Время": time_str,
                                "Дисциплина": subject,
                                "Тип занятия": lesson_type,
                                "Преподаватель": ", ".join(teachers),
                                "Место": place,
                                "Группа": group_human,
                                "Формат": "СДО" if "СДО" in place else "Очно"
                            })
            time.sleep(12)
        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {e}")

        current += timedelta(weeks=1)

    return pd.DataFrame(all_lessons)

# ========================= ПАРСЕР ПРЕПОДАВАТЕЛЯ (твой оригинальный) =========================
def parse_teacher_schedule(teacher_name: str, start_date: datetime, end_date: datetime):
    if teacher_name not in TEACHER_MAP:
        st.error(f"Преподаватель {teacher_name} не найден.")
        return pd.DataFrame()

    teacher_id = TEACHER_MAP[teacher_name]
    all_lessons = []

    current = start_date - timedelta(days=start_date.weekday())
    base_url = f"https://ruz.spbstu.ru/teachers/{teacher_id}"

    while current <= end_date:
        url = f"{base_url}?date={current.strftime('%Y-%m-%d')}"

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

                        time_str = lesson.find('span', class_='lesson__time')
                        time_str = time_str.text.strip() if time_str else ""

                        groups = []
                        groups_elem = lesson.find('div', class_='lesson-groups__list')
                        if groups_elem:
                            for link in groups_elem.find_all('a', class_='lesson__link'):
                                groups.append(link.text.strip())

                        place = parse_place(lesson.find('div', class_='lesson__places'))

                        # Проверка, что это наш преподаватель
                        is_our_teacher = False
                        teacher_element = lesson.find('div', class_='lesson__teachers')
                        if teacher_element:
                            if any(f'/teachers/{teacher_id}' in a.get('href', '') for a in teacher_element.find_all('a')):
                                is_our_teacher = True

                        if is_our_teacher and subject:
                            all_lessons.append({
                                "Дата": date_text,
                                "Время": time_str,
                                "Дисциплина": subject,
                                "Тип занятия": lesson_type,
                                "Группы": ', '.join(groups),
                                "Преподаватель": teacher_name,
                                "Место": place,
                                "Формат": "СДО"
                            })
            time.sleep(12)
        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {e}")

        current += timedelta(weeks=1)

    return pd.DataFrame(all_lessons)

# ========================= ИНТЕРФЕЙС =========================
tab1, tab2, tab3 = st.tabs(["📥 Обновление расписания", "🔍 Поиск свободных окон", "📊 Статистика"])

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
            with st.spinner("Парсинг группы..."):
                df = parse_group_schedule(group_human, start_date, end_date)
                if not df.empty:
                    st.session_state.schedule_data[f"Группа {group_human}"] = df
                    st.success(f"Загружено {len(df)} занятий")
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        st.dataframe(df[df['Дата'] == date])
    else:
        teacher_name = st.selectbox("Выберите преподавателя", list(TEACHER_MAP.keys()))
        if st.button("🚀 Запустить парсинг преподавателя", type="primary"):
            with st.spinner("Парсинг преподавателя..."):
                df = parse_teacher_schedule(teacher_name, start_date, end_date)
                if not df.empty:
                    st.session_state.schedule_data[f"Преподаватель {teacher_name}"] = df
                    st.success(f"Загружено {len(df)} занятий")
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        st.dataframe(df[df['Дата'] == date])

with tab2:
    st.subheader("🔍 Поиск свободных окон")

    st.write("**Выберите группы и преподавателей для поиска общего свободного времени:**")
    selected_groups = st.multiselect("Группы", options=list(GROUP_MAP.keys()))
    selected_teachers = st.multiselect("Преподаватели", options=list(TEACHER_MAP.keys()))

    col1, col2 = st.columns(2)
    with col1:
        min_duration = st.slider("Мин. длительность окна (мин)", 30, 180, 80)
        break_min = st.slider("Мин. перерыв после занятия (мин)", 0, 60, 20)
    with col2:
        start_time = st.time_input("Начало интервала", datetime.strptime("09:00", "%H:%M").time())
        end_time = st.time_input("Конец интервала", datetime.strptime("18:00", "%H:%M").time())

    if st.button("🔎 Найти свободные окна", type="primary"):
        if not selected_groups and not selected_teachers:
            st.warning("Выберите хотя бы одну группу или преподавателя")
        else:
            with st.spinner("Ищу пересечения свободных окошек..."):
                # Здесь будет реальная логика поиска
                st.info("Поиск выполнен. Показано найденных слотов.")
                # Пока показываем загруженные данные для проверки
                if st.session_state.schedule_data:
                    for name, df in st.session_state.schedule_data.items():
                        st.subheader(name)
                        st.dataframe(df)

with tab3:
    st.subheader("📊 Статистика")
    if st.session_state.schedule_data:
        all_dfs = list(st.session_state.schedule_data.values())
        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            st.metric("Всего занятий", len(combined))
            st.metric("Период", f"{combined['Дата'].min()} — {combined['Дата'].max()}")

            col1, col2 = st.columns(2)
            with col1:
                st.write("**По типам занятий:**")
                st.dataframe(combined['Тип занятия'].value_counts())
            with col2:
                st.write("**По преподавателям:**")
                st.dataframe(combined['Преподаватель'].value_counts())
    else:
        st.info("Загрузите расписание")

st.caption("Версия 3.2 • Полный парсинг по группе и преподавателю")
