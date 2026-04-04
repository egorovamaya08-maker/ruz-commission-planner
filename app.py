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

# Стандартная сетка пар в СПбПУ (время начала и конца)
TIME_SLOTS = [
    "08:00 – 09:35", "09:50 – 11:25", "11:40 – 13:15",
    "13:45 – 15:20", "15:35 – 17:10", "17:25 – 19:00", "19:15 – 20:50"
]

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

# ========================= ПАРСЕР ГРУППЫ (с фильтром по дате) =========================
def parse_group_schedule(group_human: str, start_date: datetime, end_date: datetime):
    if group_human not in GROUP_MAP:
        st.error(f"Группа {group_human} не найдена.")
        return pd.DataFrame()

    group_id = GROUP_MAP[group_human]
    all_lessons = []

    # Первый понедельник >= start_date
    days_ahead = 0 - start_date.weekday()
    if days_ahead < 0:
        days_ahead += 7
    current = start_date + timedelta(days=days_ahead)

    progress_bar = st.progress(0)
    status_text = st.empty()
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 1

    while current <= end_date:
        week_count += 1
        url = f"https://ruz.spbstu.ru/faculty/100/groups/{group_id}?date={current.strftime('%Y-%m-%d')}"
        status_text.text(f"Парсинг группы {group_human}: неделя {week_count}/{total_weeks} ({current.strftime('%d.%m.%Y')})")

        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for day in soup.find_all('li', class_='schedule__day'):
                    date_elem = day.find('div', class_='schedule__date')
                    if not date_elem:
                        continue
                    date_text = date_elem.text.strip()
                    # Проверяем, что дата входит в диапазон
                    try:
                        lesson_date = datetime.strptime(date_text, "%d.%m.%Y")
                        if lesson_date < start_date or lesson_date > end_date:
                            continue
                    except:
                        continue

                    for lesson in day.find_all('li', class_='lesson'):
                        subject = ""
                        subject_elem = lesson.find('div', class_='lesson__subject')
                        if subject_elem:
                            spans = subject_elem.find_all('span')
                            if spans:
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
                                "Занято кем": f"Группа {group_human}",
                                "Что": f"{subject} ({lesson_type})",
                                "Место": place,
                                "Преподаватель": ", ".join(teachers)
                            })

            progress_bar.progress(min(week_count / total_weeks, 1.0))
            time.sleep(12)
        except Exception as e:
            st.warning(f"Ошибка при парсинге группы {group_human} на неделе {current}: {e}")

        current += timedelta(weeks=1)

    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(all_lessons)

# ========================= ПАРСЕР ПРЕПОДАВАТЕЛЯ (с фильтром по дате) =========================
def parse_teacher_schedule(teacher_name: str, start_date: datetime, end_date: datetime):
    if teacher_name not in TEACHER_MAP:
        st.error(f"Преподаватель {teacher_name} не найден.")
        return pd.DataFrame()

    teacher_id = TEACHER_MAP[teacher_name]
    all_lessons = []

    days_ahead = 0 - start_date.weekday()
    if days_ahead < 0:
        days_ahead += 7
    current = start_date + timedelta(days=days_ahead)

    progress_bar = st.progress(0)
    status_text = st.empty()
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 1
    base_url = f"https://ruz.spbstu.ru/teachers/{teacher_id}"

    while current <= end_date:
        week_count += 1
        url = f"{base_url}?date={current.strftime('%Y-%m-%d')}"
        status_text.text(f"Парсинг преподавателя {teacher_name}: неделя {week_count}/{total_weeks} ({current.strftime('%d.%m.%Y')})")

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
                        if lesson_date < start_date or lesson_date > end_date:
                            continue
                    except:
                        continue

                    for lesson in day.find_all('li', class_='lesson'):
                        subject = ""
                        subject_elem = lesson.find('div', class_='lesson__subject')
                        if subject_elem:
                            spans = subject_elem.find_all('span')
                            if spans:
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
                                "Занято кем": f"Преподаватель {teacher_name}",
                                "Что": f"{subject} ({lesson_type})",
                                "Место": place,
                                "Группы": ', '.join(groups)
                            })

            progress_bar.progress(min(week_count / total_weeks, 1.0))
            time.sleep(12)
        except Exception as e:
            st.warning(f"Ошибка при парсинге преподавателя {teacher_name} на неделе {current}: {e}")

        current += timedelta(weeks=1)

    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(all_lessons)

# ========================= ПОСТРОЕНИЕ МАТРИЦЫ ЗАНЯТОСТИ =========================
def build_occupancy_matrix(schedule_dfs, start_date, end_date):
    """
    schedule_dfs: список DataFrame с полями Дата, Время, Занято кем, Что
    Возвращает DataFrame с индексом = TIME_SLOTS, колонками = даты,
    в ячейках — текст о занятости (если несколько занятий — объединяются).
    """
    if not schedule_dfs:
        return pd.DataFrame()

    combined = pd.concat(schedule_dfs, ignore_index=True)
    # Преобразуем дату в объект datetime для сортировки
    combined['Дата_obj'] = pd.to_datetime(combined['Дата'], format='%d.%m.%Y', errors='coerce')
    # Отфильтровываем по диапазону (на всякий случай)
    mask = (combined['Дата_obj'] >= pd.Timestamp(start_date)) & (combined['Дата_obj'] <= pd.Timestamp(end_date))
    combined = combined[mask].copy()
    if combined.empty:
        return pd.DataFrame()

    # Генерируем все даты диапазона
    date_range = []
    curr = start_date
    while curr <= end_date:
        date_range.append(curr.strftime("%d.%m.%Y"))
        curr += timedelta(days=1)

    # Для каждой даты и временного слота собираем информацию
    matrix_data = {date: {slot: [] for slot in TIME_SLOTS} for date in date_range}

    for _, row in combined.iterrows():
        date = row['Дата']
        time_str = row['Время']
        who = row['Занято кем']
        what = row['Что']

        # Находим, к какому стандартному слоту относится время занятия
        slot_found = None
        for slot in TIME_SLOTS:
            # Слот имеет вид "08:00 – 09:35"
            slot_start = slot.split(' – ')[0]
            try:
                lesson_start = datetime.strptime(time_str.split('–')[0].strip(), "%H:%M")
                slot_start_dt = datetime.strptime(slot_start, "%H:%M")
                # Сравниваем только часы и минуты, дата не важна
                if lesson_start >= slot_start_dt:
                    # Проверяем, что начало занятия не позже конца слота (упрощённо)
                    slot_end = slot.split(' – ')[1]
                    slot_end_dt = datetime.strptime(slot_end, "%H:%M")
                    lesson_end = datetime.strptime(time_str.split('–')[1].strip(), "%H:%M")
                    if lesson_end <= slot_end_dt:
                        slot_found = slot
                        break
            except:
                continue
        if slot_found is None:
            # Если не сопоставилось, пропускаем (редко)
            continue

        if date in matrix_data and slot_found in matrix_data[date]:
            matrix_data[date][slot_found].append(f"{who}: {what}")

    # Формируем DataFrame
    df_matrix = pd.DataFrame(index=TIME_SLOTS, columns=date_range)
    for date in date_range:
        for slot in TIME_SLOTS:
            items = matrix_data[date].get(slot, [])
            if items:
                # Объединяем несколько занятий через перенос строки
                df_matrix.at[slot, date] = "\n".join(items)
            else:
                df_matrix.at[slot, date] = ""

    return df_matrix

# ========================= ИНТЕРФЕЙС =========================
tab1, tab2, tab3 = st.tabs(["📥 Вывод расписания", "🔍 Поиск свободных окон", "📊 Статистика"])

# -------------------- ВКЛАДКА 1: ВЫВОД РАСПИСАНИЯ --------------------
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
            with st.spinner("Загрузка..."):
                df = parse_group_schedule(group_human, start_date, end_date)
                if not df.empty:
                    st.session_state.schedule_data = {f"Группа {group_human}": df}
                    st.success(f"✅ Загружено {len(df)} занятий")
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        st.dataframe(df[df['Дата'] == date].drop(columns=['Дата']), use_container_width=True)
                else:
                    st.error("Не удалось загрузить расписание")
    else:
        teacher_name = st.selectbox("Выберите преподавателя", list(TEACHER_MAP.keys()))
        if st.button("🚀 Показать расписание преподавателя", type="primary"):
            with st.spinner("Загрузка..."):
                df = parse_teacher_schedule(teacher_name, start_date, end_date)
                if not df.empty:
                    st.session_state.schedule_data = {f"Преподаватель {teacher_name}": df}
                    st.success(f"✅ Загружено {len(df)} занятий")
                    for date in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date}")
                        st.dataframe(df[df['Дата'] == date].drop(columns=['Дата']), use_container_width=True)
                else:
                    st.error("Не удалось загрузить расписание")

# -------------------- ВКЛАДКА 2: ПОИСК СВОБОДНЫХ ОКОН --------------------
with tab2:
    st.subheader("🔍 Поиск свободных окон (матрица занятости)")

    st.write("**Выберите группы и преподавателей для анализа:**")
    col_g, col_t = st.columns(2)
    with col_g:
        selected_groups = st.multiselect("Группы", options=list(GROUP_MAP.keys()))
    with col_t:
        selected_teachers = st.multiselect("Преподаватели", options=list(TEACHER_MAP.keys()))

    d1, d2 = st.columns(2)
    with d1:
        search_start = st.date_input("Начало периода поиска", datetime(2026, 2, 1), key="search_start")
    with d2:
        search_end = st.date_input("Конец периода поиска", datetime(2026, 2, 8), key="search_end")

    if st.button("🔎 Построить карту занятости", type="primary"):
        if not selected_groups and not selected_teachers:
            st.warning("Выберите хотя бы одну группу или преподавателя.")
        else:
            all_dfs = []
            # Парсим группы
            for g in selected_groups:
                with st.spinner(f"Парсинг группы {g}..."):
                    df = parse_group_schedule(g, search_start, search_end)
                    if not df.empty:
                        all_dfs.append(df)
            # Парсим преподавателей
            for t in selected_teachers:
                with st.spinner(f"Парсинг преподавателя {t}..."):
                    df = parse_teacher_schedule(t, search_start, search_end)
                    if not df.empty:
                        all_dfs.append(df)

            if not all_dfs:
                st.warning("Не удалось получить расписание для выбранных элементов.")
            else:
                matrix = build_occupancy_matrix(all_dfs, search_start, search_end)
                if matrix.empty:
                    st.info("Нет данных за выбранный период.")
                else:
                    st.markdown("### 📅 Матрица занятости")
                    st.markdown("**Зелёные ячейки — свободные окна (нет занятий).**")

                    # Для отображения заменяем пустые ячейки на "✅ СВОБОДНО"
                    display_matrix = matrix.copy()
                    display_matrix = display_matrix.fillna("")
                    display_matrix = display_matrix.applymap(lambda x: "✅ СВОБОДНО" if x == "" else x)

                    # Применяем стили: зелёный фон для свободных, розовый для занятых
                    def color_cells(val):
                        if val == "✅ СВОБОДНО":
                            return 'background-color: #d4edda; color: #155724; font-weight: bold;'
                        else:
                            return 'background-color: #f8d7da; color: #721c24;'

                    styled = display_matrix.style.applymap(color_cells)
                    st.dataframe(styled, use_container_width=True, height=600)

                    # Дополнительная легенда
                    st.caption("В ячейках указано, кто и что проводит в данное время. Если несколько занятий — они перечислены через перенос строки.")

# -------------------- ВКЛАДКА 3: СТАТИСТИКА --------------------
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

st.caption("Версия 5.0 • Матрица занятости с сеткой пар • Корректный парсинг дат")
