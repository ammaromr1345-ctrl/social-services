# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import sqlite3
from datetime import datetime
import pandas as pd
import io

import os
app = Flask(__name__, template_folder=os.path.abspath("templates"))
app.secret_key = "social_services_secret"

def init_db():
    conn = sqlite3.connect("social_web.db")
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS members(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT);
    CREATE TABLE IF NOT EXISTS grants(id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, type TEXT, amount REAL, date TEXT);
    CREATE TABLE IF NOT EXISTS loans(id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, amount REAL, repaid REAL, remaining REAL, date TEXT);
    CREATE TABLE IF NOT EXISTS installments(id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, product TEXT, total_price REAL, paid REAL, remaining REAL, date TEXT);
    CREATE TABLE IF NOT EXISTS revenues(id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, amount REAL, date TEXT);
    """)
    conn.commit(); conn.close()
init_db()

@app.route("/")
def dashboard():
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM members"); m_count = c.fetchone()[0]
    c.execute("SELECT SUM(amount) FROM grants"); g_sum = c.fetchone()[0] or 0
    c.execute("SELECT SUM(remaining) FROM loans"); l_sum = c.fetchone()[0] or 0
    c.execute("SELECT SUM(remaining) FROM installments"); i_sum = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM revenues"); r_sum = c.fetchone()[0] or 0
    conn.close()
    return render_template("dashboard.html", members_count=m_count, grants_sum=f"{g_sum:,.0f}", loans_remaining=f"{l_sum:,.0f}", install_remaining=f"{i_sum:,.0f}", revenues_sum=f"{r_sum:,.0f}")

# ===== الأعضاء =====
@app.route("/members")
def members():
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("SELECT * FROM members ORDER BY id DESC"); data = c.fetchall(); conn.close()
    return render_template("members.html", members=data)

@app.route("/add_member", methods=["POST"])
def add_member():
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("INSERT INTO members(name, phone, address) VALUES(?,?,?)", (request.form.get("name"), request.form.get("phone"), request.form.get("address")))
    conn.commit(); conn.close()
    flash("تمت إضافة العضو بنجاح!", "success")
    return redirect(url_for("members"))

# ===== المنح =====
@app.route("/grants")
def grants():
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("SELECT g.id, m.name, g.type, g.amount, g.date FROM grants g LEFT JOIN members m ON g.member_id = m.id ORDER BY g.id DESC")
    data = c.fetchall(); c.execute("SELECT id, name FROM members"); members = c.fetchall(); conn.close()
    return render_template("grants.html", grants=data, members=members)

@app.route("/add_grant", methods=["POST"])
def add_grant():
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("INSERT INTO grants(member_id, type, amount, date) VALUES(?,?,?,?)", 
              (request.form.get("member_id"), request.form.get("type"), request.form.get("amount"), datetime.now().strftime("%Y-%m-%d")))
    conn.commit(); conn.close()
    flash("تمت إضافة المنحة بنجاح!", "success")
    return redirect(url_for("grants"))

# ===== القروض =====
@app.route("/loans")
def loans():
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("SELECT l.id, m.name, l.amount, l.repaid, l.remaining, l.date FROM loans l LEFT JOIN members m ON l.member_id = m.id ORDER BY l.id DESC")
    data = c.fetchall(); c.execute("SELECT id, name FROM members"); members = c.fetchall(); conn.close()
    return render_template("loans.html", loans=data, members=members)

@app.route("/add_loan", methods=["POST"])
def add_loan():
    amt = float(request.form.get("amount"))
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("INSERT INTO loans(member_id, amount, repaid, remaining, date) VALUES(?,?,?,?,?)", 
              (request.form.get("member_id"), amt, 0, amt, datetime.now().strftime("%Y-%m-%d")))
    conn.commit(); conn.close()
    flash("تمت إضافة القرض بنجاح!", "success")
    return redirect(url_for("loans"))

@app.route("/repay_loan/<int:id>", methods=["POST"])
def repay_loan(id):
    pay = float(request.form.get("pay_amount"))
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("SELECT remaining FROM loans WHERE id=?", (id,)); rem = c.fetchone()[0]
    if pay <= rem:
        c.execute("UPDATE loans SET repaid = repaid + ?, remaining = remaining - ? WHERE id=?", (pay, pay, id))
        conn.commit(); flash("تم تسديد الدفعة بنجاح!", "success")
    else: flash("المبلغ المدفوع أكبر من المتبقي!", "danger")
    conn.close(); return redirect(url_for("loans"))

# ===== التقسيط =====
@app.route("/installments")
def installments():
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("SELECT i.id, m.name, i.product, i.total_price, i.paid, i.remaining, i.date FROM installments i LEFT JOIN members m ON i.member_id = m.id ORDER BY i.id DESC")
    data = c.fetchall(); c.execute("SELECT id, name FROM members"); members = c.fetchall(); conn.close()
    return render_template("installments.html", installments=data, members=members)

@app.route("/add_installment", methods=["POST"])
def add_installment():
    total = float(request.form.get("total"))
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("INSERT INTO installments(member_id, product, total_price, paid, remaining, date) VALUES(?,?,?,?,?,?)", 
              (request.form.get("member_id"), request.form.get("product"), total, 0, total, datetime.now().strftime("%Y-%m-%d")))
    conn.commit(); conn.close()
    flash("تمت إضافة عملية التقسيط بنجاح!", "success")
    return redirect(url_for("installments"))

@app.route("/repay_inst/<int:id>", methods=["POST"])
def repay_inst(id):
    pay = float(request.form.get("pay_amount"))
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("SELECT remaining FROM installments WHERE id=?", (id,)); rem = c.fetchone()[0]
    if pay <= rem:
        c.execute("UPDATE installments SET paid = paid + ?, remaining = remaining - ? WHERE id=?", (pay, pay, id))
        conn.commit(); flash("تم تسديد القسط بنجاح!", "success")
    else: flash("المبلغ أكبر من المتبقي!", "danger")
    conn.close(); return redirect(url_for("installments"))

# ===== الإيرادات =====
@app.route("/revenues")
def revenues():
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("SELECT * FROM revenues ORDER BY id DESC"); data = c.fetchall(); conn.close()
    return render_template("revenues.html", revenues=data)

@app.route("/add_revenue", methods=["POST"])
def add_revenue():
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("INSERT INTO revenues(source, amount, date) VALUES(?,?,?)", 
              (request.form.get("source"), request.form.get("amount"), datetime.now().strftime("%Y-%m-%d")))
    conn.commit(); conn.close()
    flash("تمت إضافة الإيراد بنجاح!", "success")
    return redirect(url_for("revenues"))

# ===== التقارير والتصدير =====
@app.route("/reports")
def reports():
    conn = sqlite3.connect("social_web.db"); c = conn.cursor()
    c.execute("SELECT type, SUM(amount), COUNT(*) FROM grants GROUP BY type"); grants_stats = c.fetchall()
    c.execute("SELECT SUM(amount) FROM revenues"); total_rev = c.fetchone()[0] or 0
    conn.close()
    return render_template("reports.html", grants_stats=grants_stats, total_rev=f"{total_rev:,.0f}")

@app.route("/export_excel")
def export_excel():
    conn = sqlite3.connect("social_web.db")
    df_g = pd.read_sql_query("SELECT g.id as 'الرقم', m.name as 'العضو', g.type as 'النوع', g.amount as 'المبلغ', g.date as 'التاريخ' FROM grants g LEFT JOIN members m ON g.member_id=m.id", conn)
    df_l = pd.read_sql_query("SELECT l.id as 'الرقم', m.name as 'العضو', l.amount as 'المبلغ', l.repaid as 'المسدد', l.remaining as 'المتبقي' FROM loans l LEFT JOIN members m ON l.member_id=m.id", conn)
    df_i = pd.read_sql_query("SELECT i.id as 'الرقم', m.name as 'العضو', i.product as 'المنتج', i.total_price as 'السعر', i.paid as 'المدفوع', i.remaining as 'المتبقي' FROM installments i LEFT JOIN members m ON i.member_id=m.id", conn)
    df_r = pd.read_sql_query("SELECT source as 'المصدر', amount as 'المبلغ', date as 'التاريخ' FROM revenues", conn)
    conn.close()
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_g.to_excel(writer, sheet_name="المنح", index=False)
        df_l.to_excel(writer, sheet_name="القروض", index=False)
        df_i.to_excel(writer, sheet_name="التقسيط", index=False)
        df_r.to_excel(writer, sheet_name="الإيرادات", index=False)
    output.seek(0)
    return send_file(output, download_name="التقرير_الشامل.xlsx", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
