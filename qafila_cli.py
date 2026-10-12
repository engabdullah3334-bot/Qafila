#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
قافلة (Qafila) - نسخة تيرمينال
=================================
أداة مساعدة تنشر بوست واحد (نص) على عدة جروبات فيسبوك بشكل يدوي متسلسل:
هي بتنسخ النص للكليبورد وتفتحلك كل جروب في المتصفح واحد ورا التاني،
وانت بس بتلصق وتضغط نشر يدويًا في فيسبوك.

ملحوظة مهمة: السكريبت ده مش بيسجل دخول على فيسبوك ومش بينشر تلقائي.
فيسبوك مبيسمحش بده لأي أداة خارجية، والمحاولة هتعرض حسابك للحظر.
كل اللي بيعمله: ينظملك عملية النسخ + فتح الجروبات بالترتيب بس.
"""

import json
import os
import sys
import webbrowser

GROUPS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "groups.json")


# ---------------------------------------------------------------------------
# تحميل/حفظ قائمة الجروبات
# ---------------------------------------------------------------------------
def load_groups():
    if not os.path.exists(GROUPS_FILE):
        return []
    try:
        with open(GROUPS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_groups(groups):
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(groups, f, ensure_ascii=False, indent=2)


def add_groups_interactively(groups):
    print("\n-- إضافة جروبات جديدة (سيب اسم الجروب فاضي وسيبه Enter عشان تخلص) --")
    while True:
        name = input("اسم الجروب: ").strip()
        if not name:
            break
        url = input("رابط الجروب: ").strip()
        if not url.startswith("http"):
            print("⚠ الرابط لازم يبدأ بـ http:// أو https:// — اتجوهل.")
            continue
        groups.append({"name": name, "url": url})
        print(f"✅ اتضاف: {name}")
    save_groups(groups)
    return groups


# ---------------------------------------------------------------------------
# نسخ للكليبورد (بدون مكتبات خارجية - بيستخدم tkinter اللي جاي مع بايثون)
# ---------------------------------------------------------------------------
def copy_to_clipboard(text):
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# اختيار الجروبات
# ---------------------------------------------------------------------------
def choose_groups(groups):
    print("\nقائمة الجروبات المتاحة:")
    for i, g in enumerate(groups, 1):
        print(f"  {i}. {g['name']}  ({g['url']})")
    print("\nاكتب أرقام الجروبات اللي عايز تنشر فيها، مفصولة بفاصلة (مثال: 1,3,4)")
    print("أو اكتب 'all' لاختيار كل الجروبات.")
    raw = input("اختيارك: ").strip().lower()
    if raw == "all":
        return list(range(len(groups)))
    indices = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(groups):
                indices.append(idx)
    return indices


# ---------------------------------------------------------------------------
# نص البوست
# ---------------------------------------------------------------------------
def get_post_text():
    print("\nاكتب نص البوست (تقدر تكتب أكتر من سطر). لما تخلص اكتب سطر فاضي مرتين ('END' لوحدها وEnter):")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# حلقة النشر المتسلسلة
# ---------------------------------------------------------------------------
def run_publish_loop(groups, chosen_indices, text):
    total = len(chosen_indices)
    done = 0
    skipped = 0
    print(f"\n=== هنبدأ نلف على {total} جروب. النص هينسخ تلقائي قبل ما نفتح كل جروب. ===\n")

    for step, idx in enumerate(chosen_indices, 1):
        g = groups[idx]
        copied = copy_to_clipboard(text)
        print(f"\n[{step}/{total}] الجروب: {g['name']}")
        if copied:
            print("📋 النص اتنسخ للكليبورد. الصقه بـ Ctrl+V (أو Cmd+V) جوه فيسبوك.")
        else:
            print("⚠ مقدرتش أنسخ النص تلقائي على الجهاز ده. انسخه يدويًا من هنا:")
            print("----------------------------------------")
            print(text)
            print("----------------------------------------")

        webbrowser.open(g["url"])
        print("↗ الجروب فتح في المتصفح.")

        while True:
            action = input("اضغط Enter لما تخلص نشر (أو اكتب s للتخطي, q للخروج): ").strip().lower()
            if action == "":
                done += 1
                break
            elif action == "s":
                skipped += 1
                break
            elif action == "q":
                print(f"\nتم إيقاف القافلة. نشرت في {done} جروب وتخطيت {skipped}.")
                sys.exit(0)

    print(f"\n🎉 خلصت القافلة! نشرت في {done} جروب من {total}، وتخطيت {skipped}.")


def main():
    print("=" * 50)
    print("   قافلة - نسخة التيرمينال")
    print("=" * 50)

    groups = load_groups()

    if not groups:
        print("\nمفيش جروبات محفوظة لسه.")
        groups = add_groups_interactively(groups)
    else:
        print(f"\nعندك {len(groups)} جروب محفوظ في {os.path.basename(GROUPS_FILE)}.")
        add_more = input("عايز تضيف جروبات جديدة؟ (y/n): ").strip().lower()
        if add_more == "y":
            groups = add_groups_interactively(groups)

    if not groups:
        print("مفيش جروبات مضافة. اطلع شغّل السكريبت تاني وضيف جروب على الأقل.")
        return

    chosen = choose_groups(groups)
    if not chosen:
        print("مفيش جروبات محددة. طلعنا.")
        return

    text = get_post_text()
    if not text.strip():
        confirm = input("النص فاضي، متأكد عايز تكمل؟ (y/n): ").strip().lower()
        if confirm != "y":
            return

    run_publish_loop(groups, chosen, text)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nتم الإيقاف.")
