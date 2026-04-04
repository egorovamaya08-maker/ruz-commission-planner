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
}

# ========================= ПАРСЕР ГРУППЫ =========================
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

    stop_button = st.button("⛔ Остановить парсинг", key="stop_group")

    while current <= end_date:
        if stop_button:
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

                        place = ""
                        place_elem = lesson.find('div', class_='lesson__places')
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
                                "Группа": group_human,
                                "Формат": "СДО" if "СДО" in place else "Очно"
                            })

            progress_bar.progress(min(week_count / total_weeks, 1.0))
            time.sleep(12)

        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {e}")

        current += timedelta(weeks=1)

    return pd.DataFrame(all_lessons)

# ========================= ПАРСЕР ПРЕПОДАВАТЕЛЯ (с фильтром по дате) =========================
def parse_teacher_schedule(teacher_name: str, start_date: datetime, end_date: datetime):
    if teacher_name not in TEACHER_MAP:
        st.error(f"Преподаватель {teacher_name} не найден.")
        return pd.DataFrame()

    teacher_id = TEACHER_MAP[teacher_name]
    all_lessons = []

    current = start_date - timedelta(days=start_date.weekday())
    progress_bar = st.progress(0)
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 2

    base_url = f"https://ruz.spbstu.ru/teachers/{teacher_id}"

    while current <= end_date:
        week_count += 1
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
                    try:
                        lesson_date = datetime.strptime(date_text, "%d.%m.%Y")
                    except:
                        continue
                    if lesson_date < start_date or lesson_date > end_date:
                        continue

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

                        if subject:
                            all_lessons.append({
                                "Дата": date_text,
                                "Время": time_str,
                                "Дисциплина": subject,
                                "Тип занятия": lesson_type,
                                "Группы": ', '.join(groups),
                                "Преподаватель": teacher_name,
                                "Формат": "СДО"
                            })

            progress_bar.progress(min(week_count / total_weeks, 1.0))
            time.sleep(12)

        except Exception as e:
            st.warning(f"Ошибка на неделе {current}: {e}")

        current += timedelta(weeks=1)

    return pd.DataFrame(all_lessons)

# ========================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПОИСКА ОКОН =========================
def fetch_schedules_for_entities(groups, teachers, start_date, end_date, progress_callback=None):
    """Парсит расписания для списка групп и преподавателей, возвращает список DataFrames."""
    all_dfs = []
    total = len(groups) + len(teachers)
    if total == 0:
        return all_dfs

    for i, group in enumerate(groups):
        if progress_callback:
            progress_callback(i / total, f"Парсинг группы {group}...")
        # Временно отключаем st.progress и кнопку остановки – для поиска используем упрощённый парсинг
        df = _quick_parse_group(group, start_date, end_date)
        if not df.empty:
            all_dfs.append(df)
    for i, teacher in enumerate(teachers):
        idx = len(groups) + i
        if progress_callback:
            progress_callback(idx / total, f"Парсинг преподавателя {teacher}...")
        df = _quick_parse_teacher(teacher, start_date, end_date)
        if not df.empty:
            all_dfs.append(df)
    return all_dfs

def _quick_parse_group(group_human, start_date, end_date):
    """Быстрый парсинг группы без UI-элементов (для поиска окон)."""
    if group_human not in GROUP_MAP:
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
                            if spans:
                                subject = spans[-1].text.strip()
                        time_str = lesson.find('span', class_='lesson__time')
                        time_str = time_str.text.strip() if time_str else ""
                        if subject and time_str:
                            all_lessons.append({
                                "Дата": date_text,
                                "Время": time_str,
                                "Дисциплина": subject,
                                "Тип": "",
                                "Преподаватель": "",
                                "Группа": group_human
                            })
            time.sleep(0.5)
        except:
            pass
        current += timedelta(weeks=1)
    return pd.DataFrame(all_lessons)

def _quick_parse_teacher(teacher_name, start_date, end_date):
    """Быстрый парсинг преподавателя без UI-элементов (для поиска окон)."""
    if teacher_name not in TEACHER_MAP:
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
                    # фильтр по дате
                    try:
                        lesson_date = datetime.strptime(date_text, "%d.%m.%Y")
                    except:
                        continue
                    if lesson_date < start_date or lesson_date > end_date:
                        continue
                    for lesson in day.find_all('li', class_='lesson'):
                        subject = ""
                        subject_elem = lesson.find('div', class_='lesson__subject')
                        if subject_elem:
                            spans = subject_elem.find_all('span')
                            if spans:
                                subject = spans[-1].text.strip()
                        time_str = lesson.find('span', class_='lesson__time')
                        time_str = time_str.text.strip() if time_str else ""
                        # Проверка, что это наш преподаватель
                        teacher_element = lesson.find('div', class_='lesson__teachers')
                        is_our = False
                        if teacher_element:
                            if teacher_element.find('a', href=f"/teachers/{teacher_id}"):
                                is_our = True
                        if is_our and subject and time_str:
                            all_lessons.append({
                                "Дата": date_text,
                                "Время": time_str,
                                "Дисциплина": subject,
                                "Тип": "",
                                "Группы": "",
                                "Преподаватель": teacher_name
                            })
            time.sleep(0.5)
        except:
            pass
        current += timedelta(weeks=1)
    return pd.DataFrame(all_lessons)

def find_intersecting_free_windows(schedule_dfs, min_duration):
    """Из списка DataFrame с расписаниями находит свободные окна (пересечение)."""
    # Собираем все занятые интервалы по датам
    busy_by_date = defaultdict(list)
    for df in schedule_dfs:
        for _, row in df.iterrows():
            date = row['Дата']
            time_str = row['Время']
            if '–' not in time_str:
                continue
            start_str, end_str = time_str.split('–')
            start_str = start_str.strip()
            end_str = end_str.strip()
            try:
                start = datetime.strptime(start_str, "%H:%M")
                end = datetime.strptime(end_str, "%H:%M")
                busy_by_date[date].append((start, end))
            except:
                continue

    # Объединяем пересекающиеся интервалы для каждой даты
    for date in busy_by_date:
        intervals = sorted(busy_by_date[date], key=lambda x: x[0])
        merged = []
        for start, end in intervals:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
        busy_by_date[date] = [(s, e) for s, e in merged]

    # Ищем свободные окна
    free_windows = []
    day_start = datetime.strptime("09:00", "%H:%M")
    day_end = datetime.strptime("18:00", "%H:%M")

    for date, busy_intervals in busy_by_date.items():
        current = day_start
        for start, end in busy_intervals:
            if start > current:
                duration = (start - current).seconds // 60
                if duration >= min_duration:
                    free_windows.append({
                        "Дата": date,
                        "Начало": current.strftime("%H:%M"),
                        "Конец": start.strftime("%H:%M"),
                        "Длительность (мин)": duration
                    })
            current = max(current, end)
        if current < day_end:
            duration = (day_end - current).seconds // 60
            if duration >= min_duration:
                free_windows.append({
                    "Дата": date,
                    "Начало": current.strftime("%H:%M"),
                    "Конец": day_end.strftime("%H:%M"),
                    "Длительность (мин)": duration
                })
    return free_windows

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
                    st.session_state.schedule_df = df
                    st.success(f"✅ Загружено {len(df)} занятий для группы {group_human}")
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        st.dataframe(df[df['Дата'] == date])
    else:
        teacher_name = st.selectbox("Выберите преподавателя", list(TEACHER_MAP.keys()))
        if st.button("🚀 Запустить парсинг преподавателя", type="primary"):
            with st.spinner("Парсинг преподавателя..."):
                df = parse_teacher_schedule(teacher_name, start_date, end_date)
                if not df.empty:
                    st.session_state.schedule_df = df
                    st.success(f"✅ Загружено {len(df)} занятий для преподавателя {teacher_name}")
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        st.dataframe(df[df['Дата'] == date])

with tab2:
    st.subheader("🔍 Поиск свободных окон (пересечение)")

    st.write("**Выберите группы и преподавателей:**")
    col_g, col_t = st.columns(2)
    with col_g:
        selected_groups = st.multiselect("Группы", options=list(GROUP_MAP.keys()), default=[])
    with col_t:
        selected_teachers = st.multiselect("Преподаватели", options=list(TEACHER_MAP.keys()), default=[])

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        search_start = st.date_input("Начало поиска", datetime(2026, 2, 1), key="search_start")
    with col_d2:
        search_end = st.date_input("Конец поиска", datetime(2026, 2, 28), key="search_end")

    duration_opts = {"30 минут": 30, "1 час": 60, "1.5 часа": 90, "2 часа": 120}
    min_duration_label = st.selectbox("Мин. длительность окна", list(duration_opts.keys()))
    min_duration = duration_opts[min_duration_label]

    if st.button("🔎 Найти свободные окна", type="primary"):
        if not selected_groups and not selected_teachers:
            st.warning("Выберите хотя бы одну группу или преподавателя.")
        else:
            # Парсим расписания для выбранных сущностей
            progress_area = st.empty()
            progress_bar = st.progress(0)
            def update_progress(frac, msg):
                progress_bar.progress(frac)
                progress_area.text(msg)
            with st.spinner("Загрузка расписаний..."):
                schedule_dfs = fetch_schedules_for_entities(
                    selected_groups, selected_teachers,
                    search_start, search_end,
                    progress_callback=update_progress
                )
            if not schedule_dfs:
                st.warning("Не удалось загрузить расписания для выбранных сущностей.")
            else:
                # Показываем общее расписание (календарь)
                st.subheader("📅 Общее расписание (все выбранные)")
                combined = pd.concat(schedule_dfs, ignore_index=True)
                if not combined.empty:
                    for date in sorted(combined['Дата'].unique()):
                        with st.expander(f"📅 {date}"):
                            st.dataframe(combined[combined['Дата'] == date].drop(columns=['Дата']), use_container_width=True)
                else:
                    st.info("Нет занятий за выбранный период.")

                # Ищем свободные окна
                st.subheader("⏰ Свободные окна (пересечение)")
                free_windows = find_intersecting_free_windows(schedule_dfs, min_duration)
                if free_windows:
                    st.success(f"✅ Найдено {len(free_windows)} окон")
                    for w in free_windows:
                        st.write(f"📅 **{w['Дата']}**: {w['Начало']} – {w['Конец']} (⏱ {w['Длительность (мин)']} мин)")
                else:
                    st.info("Нет свободных окон, удовлетворяющих условиям.")

with tab3:
    st.subheader("📊 Статистика")
    if "schedule_df" in st.session_state and not st.session_state.schedule_df.empty:
        df = st.session_state.schedule_df
        st.metric("Всего занятий", len(df))
        st.metric("Период", f"{df['Дата'].min()} — {df['Дата'].max()}")

        st.write("**По типам занятий:**")
        st.dataframe(df['Тип занятия'].value_counts())
    else:
        st.info("Загрузите расписание для просмотра статистики")

st.caption("Версия 2.0 • Поиск пересечений свободного времени • Парсинг преподавателя с фильтром по дате")
