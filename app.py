import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date
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

# ========================= КОМИССИИ (расширенный тестовый набор) =========================

COMMISSION_MEMBERS: dict[str, list[str]] = {
    "Комса1": ["Иванов Иван Иванович", "Петров Пётр Петрович", "Смирнова Анна Сергеевна"],
    "Комса2": ["Иванов Иван Иванович", "Сидоров Сидор Сидорович"],
    "Комса3": ["Петров Пётр Петрович", "Кузнецова Елена Викторовна"],
    "Комса4": ["Смирнова Анна Сергеевна", "Попов Дмитрий Александрович"],
    "Комса5": ["Иванов Иван Иванович", "Кузнецова Елена Викторовна", "Васильев Сергей Николаевич"],
    "Комса6": ["Сидоров Сидор Сидорович", "Попов Дмитрий Александрович"],
    "Комса7": ["Васильев Сергей Николаевич", "Смирнова Анна Сергеевна"],
    "Комса8": ["Кузнецова Елена Викторовна", "Петров Пётр Петрович"],
    "Комса9": ["Попов Дмитрий Александрович", "Иванов Иван Иванович"],
    "Комса10": ["Васильев Сергей Николаевич", "Сидоров Сидор Сидорович", "Кузнецова Елена Викторовна"],
    "Комса11": ["Смирнова Анна Сергеевна", "Попов Дмитрий Александрович"],
    "Комса12": ["Петров Пётр Петрович", "Васильев Сергей Николаевич"]
}

# ========================= ПАРСЕРЫ =========================
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


def parse_group_schedule(group_human: str, start_date: datetime, end_date: datetime):
    if group_human not in GROUP_MAP:
        st.error(f"Группа {group_human} не найдена.")
        return pd.DataFrame()
    group_id = GROUP_MAP[group_human]
    all_lessons = []

    current = start_date - timedelta(days=start_date.weekday())
    if current < start_date:
        current += timedelta(weeks=1)

    progress_bar = st.progress(0)
    week_count = 0
    total_weeks = ((end_date - start_date).days // 7) + 2

    while current <= end_date:
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
                    try:
                        lesson_date = datetime.strptime(date_text, "%d.%m.%Y")
                        if lesson_date < start_date or lesson_date > end_date:
                            continue
                    except:
                        pass
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
    return pd.DataFrame(all_lessons)


def parse_teacher_schedule(teacher_name: str, start_date: datetime, end_date: datetime):
    if teacher_name not in TEACHER_MAP:
        st.error(f"Преподаватель {teacher_name} не найден.")
        return pd.DataFrame()
    teacher_id = TEACHER_MAP[teacher_name]
    all_lessons = []

    current = start_date - timedelta(days=start_date.weekday())
    if current < start_date:
        current += timedelta(weeks=1)

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
                        if lesson_date < start_date or lesson_date > end_date:
                            continue
                    except:
                        pass
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
    return pd.DataFrame(all_lessons)


# ========================= ЛОГИКА КОМИССИЙ =========================
def generate_time_slots(start: date | datetime, end: date | datetime, hours: range = range(8, 21)) -> list[datetime]:
    if isinstance(start, date) and not isinstance(start, datetime):
        start = datetime.combine(start, datetime.min.time())
    if isinstance(end, date) and not isinstance(end, datetime):
        end = datetime.combine(end, datetime.min.time())

    slots = []
    current = start.replace(hour=8, minute=0, second=0, microsecond=0)
    while current.date() <= end.date():
        for h in hours:
            slot = current.replace(hour=h)
            if slot.date() > end.date():
                break
            slots.append(slot)
        current += timedelta(days=1)
    return slots


def build_empty_matrix(time_slots: list[datetime], commission_names: list[str]) -> pd.DataFrame:
    slot_labels = [s.strftime("%d.%m %H:%M") for s in time_slots]
    df = pd.DataFrame(index=slot_labels, columns=commission_names)
    df[:] = ""
    return df


def auto_mark_conflicts(matrix: pd.DataFrame, commission_members: dict) -> pd.DataFrame:
    """
    Автоматически проставляет занятость во все комиссии, 
    у которых есть общие участники с уже занятыми комиссиями
    """
    if matrix is None or matrix.empty:
        return pd.DataFrame()
    
    # Создаем копию для работы
    result_df = matrix.copy().astype(str).fillna("")
    
    # Получаем все комиссии
    comms = list(result_df.columns)
    
    # Для каждого временного слота (строки)
    for idx in result_df.index:
        # Собираем всех участников, которые уже заняты в этом слоте
        busy_members = set()
        
        # Сначала проходим по всем комиссиям и собираем занятых участников
        for comm in comms:
            cell_value = result_df.loc[idx, comm]
            if cell_value and cell_value != "nan" and "🟢" not in cell_value:
                # Если в ячейке есть текст (не пусто), значит комиссия занята
                # Добавляем всех участников этой комиссии в список занятых
                busy_members.update(commission_members.get(comm, []))
        
        # Теперь для всех комиссий, у которых есть пересечение с занятыми участниками
        for comm in comms:
            comm_members = set(commission_members.get(comm, []))
            
            # Если есть пересечение с занятыми участниками
            if comm_members & busy_members:
                current_value = result_df.loc[idx, comm]
                # Если ячейка пустая - ставим отметку о занятости
                if pd.isna(current_value) or current_value == "" or current_value == "nan":
                    result_df.loc[idx, comm] = "🟢 Занято"
                # Если уже есть текст - просто добавляем индикатор
                elif "🟢" not in current_value and "🔴" not in current_value:
                    result_df.loc[idx, comm] = f"🟢 {current_value}"
    
    return result_df

def format_header(members: list[str]) -> str:
    short = []
    for m in members:
        parts = m.split()
        if len(parts) >= 3:
            short.append(f"{parts[0]} {parts[1][0]}.{parts[2][0]}.")
        elif len(parts) >= 2:
            short.append(f"{parts[0]} {parts[1][0]}.")
        else:
            short.append(m)
    return ", ".join(short)
    
# ========================= ИНТЕРФЕЙС =========================
tab1, tab3, tab2, tab4 = st.tabs([
    "📥 Вывод расписания",
    "📊 Статистика",
    "🔍 Поиск свободных окон",
    "⚖️ Планирование комиссий"
])

# ========================= ТАБ 1: ВЫВОД РАСПИСАНИЯ =========================
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
                    for date_val in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date_val}")
                        st.dataframe(df[df['Дата'] == date_val])
    else:
        teacher_name = st.selectbox("Выберите преподавателя", list(TEACHER_MAP.keys()))
        if st.button("🚀 Показать расписание преподавателя", type="primary"):
            with st.spinner("Парсинг..."):
                df = parse_teacher_schedule(teacher_name, start_date, end_date)
                if not df.empty:
                    st.session_state.schedule_data = {f"Преподаватель {teacher_name}": df}
                    st.success(f"✅ Загружено {len(df)} занятий")
                    for date_val in sorted(df['Дата'].unique()):
                        st.subheader(f"📅 {date_val}")
                        st.dataframe(df[df['Дата'] == date_val])

# ========================= ТАБ 3: СТАТИСТИКА =========================
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

# ========================= ТАБ 2: ПОИСК СВОБОДНЫХ ОКОН =========================
with tab2:
    st.subheader("🔍 Поиск свободных окон")
    st.write("**Выберите группы и преподавателей:**")
    selected_groups = st.multiselect("Группы", options=list(GROUP_MAP.keys()))
    selected_teachers = st.multiselect("Преподаватели", options=list(TEACHER_MAP.keys()))
    col1, col2 = st.columns(2)
    with col1:
        search_start = st.date_input("Начало периода", datetime(2026, 2, 1), key="search_start")
    with col2:
        search_end = st.date_input("Конец периода", datetime(2026, 2, 28), key="search_end")
    duration_options = {"30 минут": 30, "1 час": 60, "1.5 часа": 90, "2 часа": 120}
    min_duration_label = st.selectbox("Мин. длительность окна", list(duration_options.keys()))
    min_duration = duration_options[min_duration_label]

    if st.button("🔎 Построить общее расписание", type="primary"):
        if not selected_groups and not selected_teachers:
            st.warning("Выберите хотя бы одну группу или преподавателя")
        else:
            with st.spinner("Загрузка расписаний..."):
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
                    st.success(f"Загружено расписание для {len(selected_groups)} групп и {len(selected_teachers)} преподавателей")
                    for date_val in sorted(combined['Дата'].unique()):
                        st.subheader(f"📅 {date_val}")
                        st.dataframe(combined[combined['Дата'] == date_val])
                else:
                    st.warning("Не удалось загрузить данные")

# ========================= ТАБ 4: ПЛАНИРОВАНИЕ КОМИССИЙ =========================
with tab4:
    st.subheader("⚖️ Планирование комиссий")
    st.caption("Пишите в ячейки **любое обозначение** (например: «Петров, Кузнецова», «Заседание», «Совещание 14:00» и т.д.). "
               "При сохранении автоматически подсвечиваются конфликты по общим участникам.")

    colA, colB = st.columns(2)
    with colA:
        matrix_start = st.date_input("Начало периода", datetime(2026, 4, 1).date(), key="m_start")
    with colB:
        matrix_end = st.date_input("Конец периода", datetime(2026, 4, 5).date(), key="m_end")

    if "commission_matrix" not in st.session_state or st.button("🔄 Перестроить матрицу под выбранный период"):
        time_slots = generate_time_slots(matrix_start, matrix_end)
        st.session_state.commission_matrix = build_empty_matrix(time_slots, list(COMMISSION_MEMBERS.keys()))
        st.rerun()

    column_config = {
        comm: st.column_config.TextColumn(
            format_header(COMMISSION_MEMBERS[comm]),   # используем функцию из предыдущего сообщения
            default="",
            max_chars=50,
        )
        for comm in COMMISSION_MEMBERS.keys()
    }

    edited_df = st.data_editor(
        st.session_state.commission_matrix,
        use_container_width=True,
        num_rows="fixed",
        key="commission_editor_final",
        column_config=column_config,
        hide_index=False,
    )

    if st.button("💾 Сохранить", type="primary", use_container_width=True):
        final_matrix = auto_mark_conflicts(edited_df, COMMISSION_MEMBERS)
        st.session_state.commission_matrix = final_matrix.copy()
        
        conflict_count = final_matrix.map(lambda x: "🟥" in str(x)).sum().sum()
        if conflict_count > 0:
            st.success(f"✅ Сохранено. Обнаружено конфликтов: {conflict_count}")
        else:
            st.info("✅ Сохранено.")
        
        st.rerun()
