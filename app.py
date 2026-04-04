import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import re

st.set_page_config(page_title="RUZ Planner", layout="wide")
st.title("📅 RUZ Planner")

# ========================= СЛОВАРИ =========================
GROUP_MAP = {
    "3733801/50001": "41846",
    "3733801/50002": "41847",
    "3733801/50003": "41848",
    "3733801/50004": "41849",
    "3743809/40101": "42004",
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

    progress_bar = st.progress(0)
    status_text = st.empty()

    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 2

    while current <= end_date:
        week_count += 1
        status_text.text(f"Парсинг группы {group_human} — неделя {week_count}/{total_weeks}")
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
                                "Группа": group_human
                            })

            progress_bar.progress(min(week_count / total_weeks, 1.0))
            time.sleep(12)
        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {e}")

        current += timedelta(weeks=1)

    status_text.empty()
    return pd.DataFrame(all_lessons)

# ========================= ПАРСЕР ПРЕПОДАВАТЕЛЯ =========================
def parse_teacher_schedule(teacher_name: str, start_date: datetime, end_date: datetime):
    if teacher_name not in TEACHER_MAP:
        st.error(f"Преподаватель {teacher_name} не найден.")
        return pd.DataFrame()

    teacher_id = TEACHER_MAP[teacher_name]
    all_lessons = []
    current = start_date - timedelta(days=start_date.weekday())
    base_url = f"https://ruz.spbstu.ru/teachers/{teacher_id}"

    progress_bar = st.progress(0)
    status_text = st.empty()
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 2

    while current <= end_date:
        week_count += 1
        status_text.text(f"Парсинг преподавателя {teacher_name} — неделя {week_count}/{total_weeks}")
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

                        teacher_element = lesson.find('div', class_='lesson__teachers')
                        is_our_teacher = False
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
                                "Место": place
                            })
            progress_bar.progress(min(week_count / total_weeks, 1.0))
            time.sleep(12)
        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {e}")

        current += timedelta(weeks=1)

    status_text.empty()
    return pd.DataFrame(all_lessons)

# ========================= КАЛЕНДАРЬ-МАТРИЦА =========================
def display_calendar_matrix(combined_df, start_date, end_date):
    """Простая и стабильная версия календаря-матрицы"""
    if combined_df.empty:
        st.info("Нет данных для отображения календаря.")
        return

    # Преобразуем даты в строку для надёжности
    start_str = start_date.strftime("%Y-%m-%d") if hasattr(start_date, 'strftime') else str(start_date)
    end_str = end_date.strftime("%Y-%m-%d") if hasattr(end_date, 'strftime') else str(end_date)

    # Генерируем даты
    date_range = pd.date_range(start_str, end_str)

    # Генерируем часовые слоты с 9:00 до 21:30
    slots = []
    current = datetime.strptime("09:00", "%H:%M")
    while current <= datetime.strptime("21:30", "%H:%M"):
        slot_start = current.strftime("%H:%M")
        current += timedelta(hours=1)
        slot_end = current.strftime("%H:%M")
        slots.append((f"{slot_start}–{slot_end}", slot_start, slot_end))

    st.subheader("📅 Календарь занятости (все выбранные группы и преподаватели)")

    html = "<table style='width:100%; border-collapse: collapse; font-size: 13px; text-align:center;'>"
    html += "<tr><th style='border:1px solid #ddd; padding:8px; background:#f1f1f1;'>Время</th>" 
    html += "".join(f"<th style='border:1px solid #ddd; padding:8px; background:#f1f1f1;'>{d.strftime('%d.%m (%a)')}</th>" for d in date_range) + "</tr>"

    for slot_name, slot_start_str, slot_end_str in slots:
        html += "<tr>"
        html += f"<td style='border:1px solid #ddd; padding:8px; background:#f8f9fa; font-weight:bold;'>{slot_name}</td>"

        for date in date_range:
            date_str = date.strftime("%d.%m.%Y")
            day_df = combined_df[combined_df['Дата'] == date_str]

            occupied = False
            events = []

            for _, row in day_df.iterrows():
                if '–' not in str(row.get('Время', '')):
                    continue
                try:
                    start_str, end_str = str(row['Время']).split('–')
                    start = datetime.strptime(start_str.strip(), "%H:%M")
                    end = datetime.strptime(end_str.strip(), "%H:%M")
                    slot_start_dt = datetime.strptime(slot_start_str, "%H:%M")
                    slot_end_dt = datetime.strptime(slot_end_str, "%H:%M")

                    if not (end <= slot_start_dt or start >= slot_end_dt):
                        occupied = True
                        info = f"{row.get('Дисциплина', '—')} ({row.get('Тип занятия', '')})"
                        if 'Преподаватель' in row and row['Преподаватель']:
                            info += f" — {row['Преподаватель']}"
                        elif 'Группа' in row:
                            info += f" [гр. {row['Группа']}]"
                        events.append(info)
                except:
                    continue

            if occupied:
                html += f"<td style='border:1px solid #ddd; padding:6px; background:#ffebee; vertical-align:top;'>"
                html += "<small>" + "<br>".join(events[:2]) + "</small>"
                if len(events) > 2:
                    html += f"<br><small>+{len(events)-2}</small>"
                html += "</td>"
            else:
                html += f"<td style='border:1px solid #ddd; padding:8px; background:#e8f5e9; color:#2e7d32; font-weight:bold;'>✅ Свободно</td>"

        html += "</tr>"

    html += "</table>"
    st.markdown(html, unsafe_allow_html=True)
    st.caption("✅ Зелёный = свободно для всех выбранных | 🔴 Красный = занято хотя бы у одного")
# ========================= ИНТЕРФЕЙС =========================
tab1, tab3, tab2 = st.tabs(["📥 Вывод расписания", "📊 Статистика", "🔍 Поиск свободных окон"])

with tab1:
    st.subheader("📥 Вывод расписания")

    mode = st.radio("Что выводим?", ["Расписание группы", "Расписание преподавателя"], horizontal=True)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Дата начала", datetime(2026, 2, 1))
    with col2:
        end_date = st.date_input("Дата окончания", datetime(2026, 5, 25))

    if mode == "Расписание группы":
        group_human = st.selectbox("Выберите группу", list(GROUP_MAP.keys()))
        if st.button("🚀 Показать расписание группы", type="primary"):
            with st.spinner("Парсинг..."):
                df = parse_group_schedule(group_human, start_date, end_date)
                if not df.empty:
                    st.session_state.schedule_data = {f"Группа {group_human}": df}
                    st.success(f"✅ Загружено {len(df)} занятий")
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        st.dataframe(df[df['Дата'] == date])
    else:
        teacher_name = st.selectbox("Выберите преподавателя", list(TEACHER_MAP.keys()))
        if st.button("🚀 Показать расписание преподавателя", type="primary"):
            with st.spinner("Парсинг..."):
                df = parse_teacher_schedule(teacher_name, start_date, end_date)
                if not df.empty:
                    st.session_state.schedule_data = {f"Преподаватель {teacher_name}": df}
                    st.success(f"✅ Загружено {len(df)} занятий")
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        st.dataframe(df[df['Дата'] == date])

with tab3:
    st.subheader("📊 Статистика")
    if 'schedule_data' in st.session_state and st.session_state.schedule_data:
        all_dfs = list(st.session_state.schedule_data.values())
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
        st.info("Загрузите расписание на вкладке 'Вывод расписания'")

with tab2:
    st.subheader("🔍 Поиск свободных окон")

    st.write("**Выберите группы и преподавателей:**")
    selected_groups = st.multiselect("Группы", options=list(GROUP_MAP.keys()))
    selected_teachers = st.multiselect("Преподаватели", options=list(TEACHER_MAP.keys()))

    duration_options = {"30 минут": 30, "1 час": 60, "1.5 часа": 90, "2 часа": 120}
    min_duration_label = st.selectbox("Мин. длительность окна", list(duration_options.keys()))
    min_duration = duration_options[min_duration_label]

    col1, col2 = st.columns(2)
    with col1:
        search_start = st.date_input("Начало периода", datetime(2026, 2, 1), key="search_start")
    with col2:
        search_end = st.date_input("Конец периода", datetime(2026, 2, 28), key="search_end")

    if st.button("🔎 Построить календарь занятости и найти окна", type="primary"):
        if not selected_groups and not selected_teachers:
            st.warning("Выберите хотя бы одну группу или преподавателя")
        else:
            with st.spinner("Загрузка расписаний и построение матрицы..."):
                schedule_dfs = []
                if selected_groups:
                    for g in selected_groups:
                        df = parse_group_schedule(g, search_start, search_end)
                        if not df.empty:
                            schedule_dfs.append(df)
                if selected_teachers:
                    for t in selected_teachers:
                        df = parse_teacher_schedule(t, search_start, search_end)
                        if not df.empty:
                            schedule_dfs.append(df)

                if schedule_dfs:
                    combined = pd.concat(schedule_dfs, ignore_index=True)
                    display_calendar_matrix(combined, search_start, search_end)
                else:
                    st.warning("Не удалось загрузить данные")

st.caption("Версия 4.0 • Полная визуализация календаря • Автономные вкладки")
