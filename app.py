import mysql.connector
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database import init_db, get_db_conn

app = Flask(__name__)


def _running_in_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


# ================= LANDING =================
@app.route("/")
def landing():
    return render_template("landing.html")


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    role = request.args.get("role", "student")

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT password_hash, role FROM users WHERE email=%s",
            (email,),
        )
        user = cur.fetchone()
        conn.close()

        if not user:
            error = "Account not found. Please register."
        elif user[1] != role:
            error = "Role mismatch"
        elif not check_password_hash(user[0], password):
            error = "Wrong password"
        else:
            # Redirect based on role
            if role == "staff":
                return redirect(url_for("admin"))
            else:
                return redirect(url_for("menu", email=email))

    return render_template("login.html", error=error, role=role)


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    success = None

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role")

        conn = get_db_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (email,password_hash,role) VALUES (%s,%s,%s)",
                (email, generate_password_hash(password), role),
            )
            conn.commit()
            success = "Account created successfully"
        except:
            error = "User already exists"
        conn.close()

    return render_template("register.html", error=error, success=success)


# ================= MENU =================
@app.route("/menu", methods=["GET", "POST"])
def menu():
    email = request.args.get("email")

    MENU = {
        "Chai & Beverages": [
            ("Adrak Chai", 10),
            ("Kulhad Chai", 20),
            ("Cold Coffee", 50),
            ("Cold Coffee with Ice Cream", 70),
            ("Lassi", 60),
        ],
        "Rolls": [
            ("Veg Roll", 40),
            ("Paneer Roll", 50),
            ("Egg Roll", 50),
            ("Chicken Roll", 70),
        ],
        "Snacks & Patty": [
            ("Aloo Patty", 20),
            ("Paneer Patty", 25),
            ("Egg Patty", 30),
        ],
        "Momos": [
            ("Veg Momos", 80),
            ("Paneer Momos", 100),
            ("Chicken Momos", 120),
        ],
        "Meals": [
            ("Chole Bhature", 99),
            ("Rajma Chawal", 90),
            ("Aloo Paratha", 60),
        ],
        "Cold Drinks": [
            ("Coke", 40),
            ("Pepsi", 40),
            ("Sprite", 40),
            ("Water", 20),
        ],
    }

    if request.method == "POST":
        food = request.form.get("food")
        total = request.form.get("total")

        if not food or not total:
            return "Invalid Order", 400

        conn = get_db_conn()
        cur = conn.cursor()
        # Initial status PENDING; payment_method will be set on /confirm
        cur.execute(
            "INSERT INTO orders (email,food,total,status) VALUES (%s,%s,%s,%s)",
            (email, food, total, "PENDING"),
        )
        conn.commit()
        order_id = cur.lastrowid
        conn.close()

        return render_template(
            "payment.html",
            order_id=order_id,
            email=email,
            food=food,
            total=total,
        )

    return render_template(
        "menu.html",
        email=email,
        menu=MENU,
        outlet="Taste Junction",
    )


# ================= HISTORY =================
@app.route("/history")
def history():
    email = request.args.get("email")

    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT food,total,time,status FROM orders WHERE email=%s ORDER BY time DESC",
        (email,),
    )
    orders = cur.fetchall()
    conn.close()

    return render_template("history.html", email=email, orders=orders)


# ================= ADMIN =================
@app.route("/admin", methods=["GET", "POST"])
def admin():
    conn = get_db_conn()
    cur = conn.cursor()

    if request.method == "POST":
        new_status = request.form["status"]
        order_id = request.form["order_id"]
        cur.execute(
            "UPDATE orders SET status=%s WHERE id=%s",
            (new_status, order_id),
        )
        conn.commit()

    # Show newest first
    cur.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cur.fetchall()
    conn.close()

    return render_template("admin.html", orders=orders)


# ================= TRACK =================
@app.route("/track/<int:order_id>")
def track(order_id):
    conn = get_db_conn()
    cur = conn.cursor()

    # Get this specific order
    cur.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
    order = cur.fetchone()

    # Simple "currently preparing" logic: earliest PREPARING order
    cur.execute(
        "SELECT id FROM orders WHERE status='PREPARING' ORDER BY id ASC LIMIT 1"
    )
    row = cur.fetchone()
    current_preparing = row[0] if row else None

    conn.close()

    return render_template("track.html", order=order, current_preparing=current_preparing)


# ================= BILL =================
@app.route("/confirm", methods=["POST"])
def confirm():
    order_id = request.form.get("order_id")
    payment_method = request.form.get("payment_method")
    upi_id = request.form.get("upi_id")
    card_number = request.form.get("card_number")

    card_last4 = None
    if card_number:
        digits = "".join(ch for ch in card_number if ch.isdigit())
        if len(digits) >= 4:
            card_last4 = digits[-4:]

    conn = get_db_conn()
    cur = conn.cursor()
    # Store payment method on the order (for cafeteria view)
    cur.execute(
        "UPDATE orders SET payment_method=%s WHERE id=%s",
        (payment_method, order_id),
    )

    cur.execute(
        "SELECT email,food,total,time FROM orders WHERE id=%s",
        (order_id,),
    )
    email, food, total, time = cur.fetchone()
    conn.commit()
    conn.close()

    return render_template(
        "bill.html",
        order_id=order_id,
        email=email,
        food=food,
        total=total,
        time=time,
        outlet_name="Taste Junction",
        payment_method=payment_method,
        upi_id=upi_id,
        card_last4=card_last4,
    )


# ================= RUN =================
if __name__ == "__main__":
    if _running_in_streamlit():
        from streamlit_app import main as streamlit_main

        streamlit_main()
    else:
        init_db()
        app.run(debug=True)
