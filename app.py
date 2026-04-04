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

# ========================= ПАРСЕР ГРУППЫ (с детальным прогрессом) =========================
def parse_group_schedule(group_human: str, start_date: datetime, end_date: datetime):
    if group_human not in GROUP_MAP:
        st.error(f"Группа {group_human} не найдена.")
        return pd.DataFrame()

    group_id = GROUP_MAP[group_human]
    all_lessons = []
    
    # Находим первый понедельник, который >= start_date
    days_ahead = 0 - start_date.weekday()  # weekday: пн=0, вс=6
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
        status_text.text(f"Обработка недели {week_count} из {total_weeks} (дата {current.strftime('%d.%m.%Y')})")

        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for day in soup.find_all('li', class_='schedule__day'):
                    date_elem = day.find('div', class_='schedule__date')
                    if not date_elem:
                        continue
                    date_text = date_elem.text.strip()
                    # Проверяем, что дата занятия входит в интервал [start_date, end_date]
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

    status_text.empty()
    return pd.DataFrame(all_lessons)

# ========================= ПАРСЕР ПРЕПОДАВАТЕЛЯ (с детальным прогрессом) =========================
def parse_teacher_schedule(teacher_name: str, start_date: datetime, end_date: datetime):
    if teacher_name not in TEACHER_MAP:
        st.error(f"Преподаватель {teacher_name} не найден.")
        return pd.DataFrame()

    teacher_id = TEACHER_MAP[teacher_name]
    all_lessons = []
    
    # Находим первый понедельник, который >= start_date
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
        status_text.text(f"Обработка недели {week_count} из {total_weeks} (дата {current.strftime('%d.%m.%Y')})")

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

    status_text.empty()
    return pd.DataFrame(all_lessons)





def display_calendar_matrix(combined_df, selected_groups, selected_teachers, start_date, end_date, time_step):
    """Отображает календарь-матрицу занятости"""
    if combined_df.empty:
        st.info("Нет занятий за выбранный период.")
        return
    
    # Преобразуем даты
    date_range = pd.date_range(start_date, end_date)
    # Определяем временные слоты
    if time_step == "По парам (1-я, 2-я...)":
        # Стандартные пары: 1-я 9:00-10:30, 2-я 10:40-12:10, 3-я 12:20-13:50, 4-я 14:00-15:30, 5-я 15:40-17:10, 6-я 17:20-18:50
        slots = [
            ("1 пара", "09:00", "10:30"),
            ("2 пара", "10:40", "12:10"),
            ("3 пара", "12:20", "13:50"),
            ("4 пара", "14:00", "15:30"),
            ("5 пара", "15:40", "17:10"),
            ("6 пара", "17:20", "18:50"),
        ]
    else:
        # 30-минутные интервалы с 9:00 до 18:00
        slots = []
        current = datetime.strptime("09:00", "%H:%M")
        end = datetime.strptime("18:00", "%H:%M")
        while current < end:
            slot_start = current.strftime("%H:%M")
            current += timedelta(minutes=30)
            slot_end = current.strftime("%H:%M")
            slots.append((f"{slot_start}-{slot_end}", slot_start, slot_end))
    
    # Подготовим данные: для каждой даты и временного интервала определим, занято или нет
    # Создадим словарь: (date_str, slot_index) -> список событий (для групп и преподавателей)
    cell_data = {}
    
    # Разбираем все занятия из combined_df
    for _, row in combined_df.iterrows():
        date_str = row['Дата']
        try:
            lesson_date = datetime.strptime(date_str, "%d.%m.%Y")
        except:
            continue
        time_range = row['Время']
        if '–' not in time_range:
            continue
        start_str, end_str = time_range.split('–')
        start_str = start_str.strip()
        end_str = end_str.strip()
        try:
            start_dt = datetime.strptime(start_str, "%H:%M")
            end_dt = datetime.strptime(end_str, "%H:%M")
        except:
            continue
        
        # Определяем, какие слоты перекрывает это занятие
        for idx, (slot_name, slot_start_str, slot_end_str) in enumerate(slots):
            slot_start = datetime.strptime(slot_start_str, "%H:%M")
            slot_end = datetime.strptime(slot_end_str, "%H:%M")
            # Если занятие пересекается со слотом
            if not (end_dt <= slot_start or start_dt >= slot_end):
                key = (date_str, idx)
                if key not in cell_data:
                    cell_data[key] = []
                # Добавляем информацию о занятии
                info = f"{row['Дисциплина']} ({row.get('Тип занятия', '')})"
                if 'Группа' in row:
                    info += f" [гр. {row['Группа']}]"
                elif 'Группы' in row and row['Группы']:
                    info += f" [гр. {row['Группы']}]"
                if 'Преподаватель' in row and row['Преподаватель']:
                    info += f" (преп. {row['Преподаватель']})"
                cell_data[key].append(info)
    
    # Строим HTML-таблицу
    st.markdown("### Календарь занятости")
    # Заголовок: даты
    header_cells = "<th>Время</th>" + "".join(f"<th>{d.strftime('%d.%m (%a)')}</th>" for d in date_range)
    html = f"<table style='border-collapse: collapse; width: 100%; font-size: 12px;'>"
    html += f"<tr>{header_cells}</tr>"
    
    for idx, (slot_name, _, _) in enumerate(slots):
        html += "<tr>"
        html += f"<td style='border: 1px solid #ddd; padding: 5px; background-color: #f2f2f2; font-weight: bold;'>{slot_name}</td>"
        for date in date_range:
            date_str = date.strftime("%d.%m.%Y")
            key = (date_str, idx)
            if key in cell_data:
                # Ячейка занята
                events = "<br>".join(cell_data[key][:3])  # не более 3 событий
                if len(cell_data[key]) > 3:
                    events += f"<br>+{len(cell_data[key])-3} ещё"
                html += f"<td style='border: 1px solid #ddd; padding: 5px; background-color: #ffcccc;'>📌 {events}</td>"
            else:
                # Свободная ячейка
                # Проверяем, что все выбранные сущности свободны (уже и так свободно, т.к. нет событий)
                html += f"<td style='border: 1px solid #ddd; padding: 5px; background-color: #ccffcc; text-align: center;'>✅ Свободно</td>"
        html += "</tr>"
    html += "</table>"
    
    st.markdown(html, unsafe_allow_html=True)
    st.caption("✅ Зелёные ячейки — все выбранные группы и преподаватели свободны. 🔴 Красные — есть занятия хотя бы у одного.")

# ========================= ИНТЕРФЕЙС =========================
tab1, tab3, tab2 = st.tabs(["📥 Вывод расписания", "📊 Статистика", "🔍 Поиск свободных окон"])

# ====================== ВКЛАДКА 1: ВЫВОД РАСПИСАНИЯ ======================
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

# ====================== ВКЛАДКА 2: СТАТИСТИКА ======================
with tab2:
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


# ====================== ВКЛАДКА 3: ПОИСК СВОБОДНЫХ ОКОН (КАЛЕНДАРЬ-МАТРИЦА) ======================
with tab3:
    
    st.subheader("🔍 Поиск свободных окон (календарь занятости)")

    st.write("**Выберите группы и преподавателей:**")
    selected_groups = st.multiselect("Группы", options=list(GROUP_MAP.keys()))
    selected_teachers = st.multiselect("Преподаватели", options=list(TEACHER_MAP.keys()))

    col_period1, col_period2 = st.columns(2)
    with col_period1:
        search_start = st.date_input("Начало периода", datetime(2026, 2, 1), key="search_start")
    with col_period2:
        search_end = st.date_input("Конец периода", datetime(2026, 2, 28), key="search_end")

    # Выбор временного шага: по парам или по часам
    time_step = st.radio("Шаг времени", ["По парам (1-я, 2-я...)", "30-минутные интервалы"], index=0)
    
    if st.button("🔎 Построить календарь занятости", type="primary"):
        if not selected_groups and not selected_teachers:
            st.warning("Выберите хотя бы одну группу или преподавателя")
        else:
            with st.spinner("Загрузка расписаний..."):
                # Загружаем расписания групп
                group_dfs = []
                for g in selected_groups:
                    df = parse_group_schedule(g, search_start, search_end)
                    if not df.empty:
                        group_dfs.append(df)
                # Загружаем расписания преподавателей
                teacher_dfs = []
                for t in selected_teachers:
                    df = parse_teacher_schedule(t, search_start, search_end)
                    if not df.empty:
                        teacher_dfs.append(df)

            if not group_dfs and not teacher_dfs:
                st.warning("Не удалось загрузить расписания для выбранных элементов.")
            else:
                # Объединяем все расписания (для групп и преподавателей)
                all_dfs = group_dfs + teacher_dfs
                combined = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
                
                # Формируем календарь
                display_calendar_matrix(combined, selected_groups, selected_teachers, search_start, search_end, time_step)
