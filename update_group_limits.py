#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from app.models import Group

def update_group_limits():
    with app.app_context():
        print("Обновление лимитов студентов в группах...")
        
        groups = Group.query.all()
        print(f"Найдено {len(groups)} групп")
        
        for group in groups:
            print(f"  Группа {group.name}: текущий лимит {group.max_students}")
        
        for group in groups:
            group.max_students = 25
        
        db.session.commit()
        print("Лимиты обновлены!")
        
        for group in groups:
            print(f"  Группа {group.name}: новый лимит {group.max_students}")

if __name__ == '__main__':
    update_group_limits()
