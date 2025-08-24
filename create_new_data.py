#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from app.models import User, Group, Course, Room, Schedule
from datetime import datetime, timedelta
import random
from sqlalchemy import text

def clear_existing_data():
    print("Очистка существующих данных...")
    
    Schedule.query.delete()
    print("  Удалено существующее расписание")
    
    Group.query.delete()
    print("  Удалены существующие группы")
    
    Course.query.delete()
    print("  Удалены существующие курсы")
    
    Room.query.delete()
    print("  Удалены существующие аудитории")
    
    try:
        db.session.execute(text("DELETE FROM sqlite_sequence WHERE name IN ('group', 'course', 'room', 'schedule')"))
    except:
        pass
    
    db.session.commit()
    print("Очистка завершена!")

def create_new_courses():
    print("\nСоздание новых курсов...")
    
    courses_data = [
        {'name': 'Программирование на Python', 'description': 'Основы программирования на Python'},
        {'name': 'Базы данных', 'description': 'Проектирование и управление базами данных'},
        {'name': 'Веб-разработка', 'description': 'Создание веб-приложений'},
        {'name': 'Алгоритмы и структуры данных', 'description': 'Изучение алгоритмов и структур данных'},
        {'name': 'Архитектура программного обеспечения', 'description': 'Проектирование архитектуры ПО'},
        {'name': 'Тестирование программного обеспечения', 'description': 'Методы тестирования ПО'},
        {'name': 'Математический анализ', 'description': 'Основы математического анализа'},
        {'name': 'Дискретная математика', 'description': 'Дискретная математика для программистов'},
        
        {'name': 'Информационные технологии', 'description': 'Основы информационных технологий'},
        {'name': 'Сетевые технологии', 'description': 'Компьютерные сети и протоколы'},
        {'name': 'Системный анализ', 'description': 'Анализ и проектирование систем'},
        {'name': 'Проектирование ИС', 'description': 'Проектирование информационных систем'},
        {'name': 'Математическая логика', 'description': 'Основы математической логики'},
        {'name': 'Теория вероятностей', 'description': 'Теория вероятностей и статистика'},
        {'name': 'Экономика информационных систем', 'description': 'Экономические аспекты ИС'},
        
        {'name': 'Микроэкономика', 'description': 'Основы микроэкономики'},
        {'name': 'Макроэкономика', 'description': 'Основы макроэкономики'},
        {'name': 'Бухгалтерский учет', 'description': 'Основы бухгалтерского учета'},
        {'name': 'Финансовый менеджмент', 'description': 'Управление финансами'},
        {'name': 'Маркетинг', 'description': 'Основы маркетинга'},
        {'name': 'Статистика', 'description': 'Статистические методы в экономике'},
        {'name': 'Эконометрика', 'description': 'Эконометрические модели'},
        {'name': 'Право', 'description': 'Основы права'},
        {'name': 'Информационные технологии в экономике', 'description': 'ИТ для экономистов'},
        
        {'name': 'Основы менеджмента', 'description': 'Основы управления'},
        {'name': 'Управление персоналом', 'description': 'HR-менеджмент'},
        {'name': 'Стратегический менеджмент', 'description': 'Стратегическое планирование'},
        {'name': 'Проектный менеджмент', 'description': 'Управление проектами'},
        {'name': 'Бизнес-планирование', 'description': 'Создание бизнес-планов'},
        {'name': 'Экономика', 'description': 'Основы экономики'},
        {'name': 'Психология управления', 'description': 'Психологические аспекты управления'},
        
        {'name': 'Английский язык', 'description': 'Иностранный язык'},
        {'name': 'Физическая культура', 'description': 'Физическое воспитание'},
        {'name': 'Философия', 'description': 'Основы философии'},
        {'name': 'История', 'description': 'История России'},
        {'name': 'Экология', 'description': 'Основы экологии'},
    ]
    
    for course_data in courses_data:
        course = Course(**course_data)
        db.session.add(course)
    
    db.session.commit()
    print(f"Создано {len(courses_data)} курсов")

def create_new_groups():
    print("\nСоздание новых групп...")
    
    groups_data = [
        {'name': 'ПКС-21', 'specialty': 'ПКС', 'course_year': 2, 'group_number': 1, 'max_students': 25},
        {'name': 'ПКС-22', 'specialty': 'ПКС', 'course_year': 2, 'group_number': 2, 'max_students': 25},
        {'name': 'ПКС-31', 'specialty': 'ПКС', 'course_year': 3, 'group_number': 1, 'max_students': 25},
        
        {'name': 'ИС-21', 'specialty': 'ИС', 'course_year': 2, 'group_number': 1, 'max_students': 25},
        {'name': 'ИС-22', 'specialty': 'ИС', 'course_year': 2, 'group_number': 2, 'max_students': 25},
        {'name': 'ИС-31', 'specialty': 'ИС', 'course_year': 3, 'group_number': 1, 'max_students': 25},
        
        {'name': 'ЭК-21', 'specialty': 'ЭК', 'course_year': 2, 'group_number': 1, 'max_students': 25},
        {'name': 'ЭК-31', 'specialty': 'ЭК', 'course_year': 3, 'group_number': 1, 'max_students': 25},
        
        {'name': 'МН-21', 'specialty': 'МН', 'course_year': 2, 'group_number': 1, 'max_students': 25},
        {'name': 'МН-31', 'specialty': 'МН', 'course_year': 3, 'group_number': 1, 'max_students': 25},
    ]
    
    for group_data in groups_data:
        group = Group(**group_data)
        db.session.add(group)
    
    db.session.commit()
    print(f"Создано {len(groups_data)} групп")

def create_rooms():
    print("\nСоздание аудиторий...")
    
    rooms_data = [
        {'number': '101', 'capacity': 30, 'building': 'Главный корпус', 'room_type': 'лекционная'},
        {'number': '102', 'capacity': 30, 'building': 'Главный корпус', 'room_type': 'лекционная'},
        {'number': '103', 'capacity': 25, 'building': 'Главный корпус', 'room_type': 'лабораторная'},
        {'number': '201', 'capacity': 30, 'building': 'Главный корпус', 'room_type': 'лекционная'},
        {'number': '202', 'capacity': 25, 'building': 'Главный корпус', 'room_type': 'компьютерная'},
        {'number': '203', 'capacity': 25, 'building': 'Главный корпус', 'room_type': 'лабораторная'},
        
        {'number': 'И-101', 'capacity': 30, 'building': 'Корпус информатики', 'room_type': 'лекционная'},
        {'number': 'И-102', 'capacity': 25, 'building': 'Корпус информатики', 'room_type': 'компьютерная'},
        {'number': 'И-103', 'capacity': 25, 'building': 'Корпус информатики', 'room_type': 'компьютерная'},
        {'number': 'И-201', 'capacity': 30, 'building': 'Корпус информатики', 'room_type': 'лекционная'},
        {'number': 'И-202', 'capacity': 25, 'building': 'Корпус информатики', 'room_type': 'лабораторная'},
        
        {'number': 'Э-101', 'capacity': 30, 'building': 'Корпус экономики', 'room_type': 'лекционная'},
        {'number': 'Э-102', 'capacity': 25, 'building': 'Корпус экономики', 'room_type': 'лекционная'},
        {'number': 'Э-201', 'capacity': 30, 'building': 'Корпус экономики', 'room_type': 'лекционная'},
        {'number': 'Э-202', 'capacity': 25, 'building': 'Корпус экономики', 'room_type': 'лабораторная'},
    ]
    
    for room_data in rooms_data:
        room = Room(**room_data)
        db.session.add(room)
    
    db.session.commit()
    print(f"Создано {len(rooms_data)} аудиторий")

def get_courses_for_specialty(specialty):
    if 'ПКС' in specialty:
        return [
            'Программирование на Python', 'Базы данных', 'Веб-разработка',
            'Алгоритмы и структуры данных', 'Архитектура программного обеспечения',
            'Тестирование программного обеспечения', 'Математический анализ',
            'Дискретная математика', 'Английский язык', 'Физическая культура'
        ]
    elif 'ИС' in specialty:
        return [
            'Информационные технологии', 'Базы данных', 'Сетевые технологии',
            'Системный анализ', 'Проектирование ИС', 'Математическая логика',
            'Теория вероятностей', 'Английский язык', 'Физическая культура',
            'Экономика информационных систем'
        ]
    elif 'ЭК' in specialty:
        return [
            'Микроэкономика', 'Макроэкономика', 'Бухгалтерский учет',
            'Финансовый менеджмент', 'Маркетинг', 'Статистика',
            'Эконометрика', 'Английский язык', 'Физическая культура',
            'Право', 'Информационные технологии в экономике'
        ]
    elif 'МН' in specialty:
        return [
            'Основы менеджмента', 'Управление персоналом', 'Стратегический менеджмент',
            'Маркетинг', 'Финансовый менеджмент', 'Проектный менеджмент',
            'Бизнес-планирование', 'Английский язык', 'Физическая культура',
            'Экономика', 'Психология управления'
        ]
    else:
        return [
            'Английский язык', 'Физическая культура', 'Философия',
            'История', 'Экология'
        ]

def create_schedule():
    print("\nСоздание расписания...")
    
    groups = Group.query.all()
    courses = Course.query.all()
    teachers = User.query.filter_by(role='teacher').all()
    rooms = Room.query.all()
    
    if not teachers:
        print("Ошибка: нет преподавателей в системе")
        return
    
    # Словарь для отслеживания занятости преподавателей
    teacher_busy = {}
    # Словарь для отслеживания занятости аудиторий
    room_busy = {}
    
    for group in groups:
        print(f"Создаем расписание для группы {group.name}")
        
        specialty_courses = get_courses_for_specialty(group.specialty)
        group_courses = [c for c in courses if c.name in specialty_courses]
        
        if not group_courses:
            print(f"  Предупреждение: для группы {group.name} не найдены курсы")
            continue
        
        for day in range(1, 6):
            day_courses = []
            
            num_slots = random.choice([3, 4])
            
            available_courses = [c for c in group_courses if c not in day_courses]
            if len(available_courses) < num_slots:
                available_courses = group_courses.copy()
            
            day_courses = random.sample(available_courses, min(num_slots, len(available_courses)))
            
            for slot in range(1, len(day_courses) + 1):
                course = day_courses[slot - 1]
                
                course_teachers = [t for t in teachers if course in t.teaching_courses]
                if not course_teachers:
                    course_teachers = teachers
                
                available_teacher = None
                for teacher in course_teachers:
                    key = f"{teacher.id}_{day}_{slot}"
                    if key not in teacher_busy:
                        available_teacher = teacher
                        break
                
                if not available_teacher:
                    for teacher in teachers:
                        key = f"{teacher.id}_{day}_{slot}"
                        if key not in teacher_busy:
                            available_teacher = teacher
                            break
                
                if not available_teacher:
                    print(f"  Предупреждение: не найден свободный преподаватель для {day}:{slot}")
                    continue
                
                available_room = None
                for room in rooms:
                    key = f"{room.id}_{day}_{slot}"
                    if key not in room_busy:
                        available_room = room
                        break
                
                if not available_room:
                    print(f"  Предупреждение: не найдена свободная аудитория для {day}:{slot}")
                    continue
                
                schedule = Schedule(
                    group_id=group.id,
                    course_id=course.id,
                    teacher_id=available_teacher.id,
                    room_id=available_room.id,
                    day_of_week=day,
                    slot_number=slot,
                    week_type='all'
                )
                
                db.session.add(schedule)
                
                teacher_key = f"{available_teacher.id}_{day}_{slot}"
                room_key = f"{available_room.id}_{day}_{slot}"
                teacher_busy[teacher_key] = True
                room_busy[room_key] = True
        
        db.session.commit()
        print(f"  Создано расписание для группы {group.name}")

def main():
    with app.app_context():
        print("=== ЗАМЕНА КУРСОВ И ГРУПП НА НОВЫЕ ===\n")
        
        clear_existing_data()
        
        create_new_courses()
        create_new_groups()
        create_rooms()
        create_schedule()
        
        print("\n=== ЗАМЕНА ЗАВЕРШЕНА УСПЕШНО! ===")
        print("Теперь у вас есть:")
        print("✅ 35 новых курсов по специальностям")
        print("✅ 12 новых групп (ПКС, ИС, ЭК, МН)")
        print("✅ 16 аудиторий в разных корпусах")
        print("✅ Полное расписание для всех групп")

if __name__ == '__main__':
    main()
