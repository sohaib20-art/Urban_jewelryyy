import os, sqlite3, secrets, json
from urllib.parse import quote
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "urban_jewelry.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
TARIFFS_PATH = BASE_DIR / "delivery_tariffs.json"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_IMAGE_MB = 5
MAX_PRODUCT_IMAGES = 8
DEFAULT_DELIVERY_TARIFFS = {
    1:[1100,600],2:[700,400],3:[900,500],4:[800,400],5:[800,400],6:[700,400],7:[900,500],8:[1100,600],9:[500,250],10:[650,400],
    11:[1300,800],12:[800,500],13:[800,400],14:[800,400],15:[650,400],16:[400,200],17:[900,500],18:[700,400],19:[700,400],20:[800,400],
    21:[700,400],22:[700,400],23:[700,400],24:[800,400],25:[700,400],26:[600,400],27:[700,400],28:[800,500],29:[700,400],30:[1000,500],
    31:[700,400],32:[1000,500],33:[1300,600],34:[700,400],35:[600,350],36:[800,400],37:[1300,600],38:[800,400],39:[900,500],40:[800,500],
    41:[800,500],42:[600,350],43:[700,400],44:[600,400],45:[1000,500],46:[700,500],47:[1000,500],48:[700,400],49:[1300,600],
    51:[900,500],52:[1300,0],53:[1300,600],55:[900,0],57:[900,0],58:[1000,500]
}
WILAYA_NAMES = {
 1:'Adrar',2:'Chlef',3:'Laghouat',4:'Oum El Bouaghi',5:'Batna',6:'Béjaïa',7:'Biskra',8:'Béchar',9:'Blida',10:'Bouira',
 11:'Tamanrasset',12:'Tébessa',13:'Tlemcen',14:'Tiaret',15:'Tizi Ouzou',16:'Alger',17:'Djelfa',18:'Jijel',19:'Sétif',20:'Saïda',
 21:'Skikda',22:'Sidi Bel Abbès',23:'Annaba',24:'Guelma',25:'Constantine',26:'Médéa',27:'Mostaganem',28:"M'Sila",29:'Mascara',30:'Ouargla',
 31:'Oran',32:'El Bayadh',33:'Illizi',34:'Bordj Bou Arreridj',35:'Boumerdès',36:'El Tarf',37:'Tindouf',38:'Tissemsilt',39:'El Oued',40:'Khenchela',
 41:'Souk Ahras',42:'Tipaza',43:'Mila',44:'Aïn Defla',45:'Naâma',46:'Aïn Témouchent',47:'Ghardaïa',48:'Relizane',49:'Timimoun',
 50:'Bordj Badji Mokhtar',51:'Ouled Djellal',52:'Béni Abbès',53:'In Salah',54:'In Guezzam',55:'Touggourt',56:'Djanet',57:'El M’Ghair',58:'El Menia'
}

def get_delivery_tariffs():
    if TARIFFS_PATH.exists():
        try:
            raw = json.loads(TARIFFS_PATH.read_text(encoding="utf-8"))
            return {int(k): [int(v[0]), int(v[1])] for k, v in raw.items() if isinstance(v, list) and len(v) == 2}
        except (ValueError, TypeError, OSError):
            pass
    return dict(DEFAULT_DELIVERY_TARIFFS)


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_MB * MAX_PRODUCT_IMAGES * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

# Change ADMIN_PASSWORD before publishing the site. Default is only for first local test.
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "UrbanSecure2026!")
ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD)

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_fr TEXT NOT NULL,
            name_ar TEXT NOT NULL DEFAULT '',
            description_fr TEXT DEFAULT '',
            description_ar TEXT DEFAULT '',
            price REAL NOT NULL,
            image TEXT DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            price REAL NOT NULL,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            wilaya TEXT NOT NULL,
            municipality TEXT NOT NULL,
            address TEXT DEFAULT '',
            delivery_type TEXT NOT NULL,
            note TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Nouvelle',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE SET NULL
        )""")
        columns = {row[1] for row in con.execute("PRAGMA table_info(orders)").fetchall()}
        if "delivery_fee" not in columns:
            con.execute("ALTER TABLE orders ADD COLUMN delivery_fee REAL NOT NULL DEFAULT 0")
        if "total_price" not in columns:
            con.execute("ALTER TABLE orders ADD COLUMN total_price REAL NOT NULL DEFAULT 0")
        if "quantity" not in columns:
            con.execute("ALTER TABLE orders ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1")

def is_allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_language():
    return {"lang": session.get("lang", "fr")}

@app.route("/lang/<language>")
def set_language(language):
    if language in ("fr", "ar"):
        session["lang"] = language
    return redirect(request.referrer or url_for("index"))

@app.route("/")
def index():
    with db() as con:
        products = con.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC").fetchall()
    return render_template("index.html", products=products)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    with db() as con:
        product = con.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if not product:
        abort(404)
    images = [name for name in (product["image"] or "").split(",") if name]
    return render_template("product_detail.html", product=product, images=images)

@app.route("/order/<int:product_id>", methods=["GET", "POST"])
def order(product_id):
    with db() as con:
        product = con.execute("SELECT * FROM products WHERE id=? AND active=1", (product_id,)).fetchone()
    if not product:
        abort(404)
    if request.method == "POST":
        name = request.form.get("customer_name", "").strip()
        phone = request.form.get("phone", "").strip()
        wilaya = request.form.get("wilaya", "").strip()
        municipality = request.form.get("municipality", "").strip()
        address = request.form.get("address", "").strip()
        delivery_type = request.form.get("delivery_type", "")
        note = request.form.get("note", "").strip()
        try:
            quantity = int(request.form.get("quantity", "1"))
            if quantity < 1 or quantity > 50:
                raise ValueError()
        except ValueError:
            flash("Quantité invalide (1 à 50).", "error")
            return render_template("order.html", product=product)
        delivery_tariffs = get_delivery_tariffs()
        try:
            wilaya_code = int(wilaya.split(' — ')[0].strip())
        except (ValueError, IndexError):
            wilaya_code = 0
        tariffs = delivery_tariffs.get(wilaya_code)
        if tariffs is None:
            flash("Le tarif de livraison pour cette wilaya n’est pas indiqué sur le tableau fourni. Contactez la boutique.", "error")
            return render_template("order.html", product=product)
        delivery_fee = tariffs[0] if delivery_type == "home" else tariffs[1]
        product_subtotal = float(product["price"]) * quantity
        total_price = product_subtotal + delivery_fee
        if not all([name, phone, wilaya, municipality]) or delivery_type not in ("home", "office"):
            flash("Veuillez remplir tous les champs obligatoires. / يرجى ملء جميع الخانات الإلزامية.", "error")
            return render_template("order.html", product=product)
        if delivery_type == "home" and not address:
            flash("L'adresse est obligatoire pour la livraison à domicile. / العنوان ضروري للتوصيل للمنزل.", "error")
            return render_template("order.html", product=product)
        with db() as con:
            cur = con.execute("""INSERT INTO orders
                (product_id, product_name, price, customer_name, phone, wilaya, municipality, address, delivery_type, note, delivery_fee, total_price, quantity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (product["id"], product["name_fr"], product_subtotal, name, phone, wilaya, municipality, address, delivery_type, note, delivery_fee, total_price, quantity))
            order_id = cur.lastrowid
        message = (
            f"Bonjour Urban.jewelryyy ! Commande #{order_id}\\n"
            f"Produit : {product['name_fr']}\\nQuantité : {quantity}\\nSous-total produits : {product_subtotal:.0f} DA\\n"
            f"Nom : {name}\\nTéléphone : {phone}\\nWilaya : {wilaya}\\n"
            f"Commune : {municipality}\\nLivraison : {'À domicile' if delivery_type == 'home' else 'Bureau de livraison'}\\nFrais de livraison : {delivery_fee:.0f} DA\\nTOTAL : {total_price:.0f} DA\\n"
            f"Adresse : {address or 'Non renseignée'}\\nNote : {note or 'Aucune'}"
        )
        return render_template("order_success.html", order_id=order_id, whatsapp_url="https://wa.me/213550329112?text=" + quote(message), product_price=product_subtotal, delivery_fee=delivery_fee, total_price=total_price)
    return render_template("order.html", product=product)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        password = request.form.get("password", "")
        # Compare against environment password; no password is stored in the database.
        if secrets.compare_digest(password, ADMIN_PASSWORD):
            session.clear()
            session["admin_logged_in"] = True
            session["lang"] = request.form.get("lang", "fr")
            return redirect(url_for("admin_dashboard"))
        flash("Mot de passe incorrect. / كلمة السر غير صحيحة.", "error")
    return render_template("admin_login.html")

@app.route("/api/delivery-tariffs")
def api_delivery_tariffs():
    return {str(k): v for k, v in get_delivery_tariffs().items()}

@app.route("/admin/tariffs/update", methods=["POST"])
@admin_required
def update_delivery_tariff():
    try:
        code = int(request.form.get("wilaya_code", "0"))
        home = int(request.form.get("home_fee", "-1"))
        office = int(request.form.get("office_fee", "-1"))
        if code not in range(1, 59) or min(home, office) < 0 or max(home, office) > 100000:
            raise ValueError()
    except ValueError:
        flash("Tarif invalide.", "error")
        return redirect(url_for("admin_dashboard") + "#tariffs")
    tariffs = get_delivery_tariffs()
    tariffs[code] = [home, office]
    TARIFFS_PATH.write_text(json.dumps({str(k): v for k, v in tariffs.items()}, ensure_ascii=False, indent=2), encoding="utf-8")
    flash("Tarifs de livraison mis à jour.", "success")
    return redirect(url_for("admin_dashboard") + "#tariffs")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("Vous êtes déconnecté. / تم تسجيل الخروج.", "success")
    return redirect(url_for("index"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    with db() as con:
        products = con.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
        orders = con.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    tariffs = [{"code": code, "name": WILAYA_NAMES.get(code, f"Wilaya {code}"), "home": get_delivery_tariffs().get(code, [None, None])[0], "office": get_delivery_tariffs().get(code, [None, None])[1]} for code in range(1, 59)]
    return render_template("admin.html", products=products, orders=orders, tariffs=tariffs)

@app.route("/admin/products/add", methods=["POST"])
@admin_required
def add_product():
    name_fr = request.form.get("name_fr", "").strip()
    name_ar = request.form.get("name_ar", "").strip()
    desc_fr = request.form.get("description_fr", "").strip()
    desc_ar = request.form.get("description_ar", "").strip()
    price_raw = request.form.get("price", "").replace(",", ".").strip()
    image_files = [f for f in request.files.getlist("images") if f and f.filename]
    if len(image_files) > MAX_PRODUCT_IMAGES:
        flash("Maximum 8 images par produit. / الحد الأقصى 8 صور لكل منتج.", "error")
        return redirect(url_for("admin_dashboard"))
    for image_file in image_files:
        if not is_allowed(image_file.filename):
            flash("Format image accepté : PNG, JPG, WEBP ou GIF. / الصيغ المقبولة: PNG أو JPG أو WEBP أو GIF.", "error")
            return redirect(url_for("admin_dashboard"))
    if not name_fr or not price_raw:
        flash("Le nom du produit et le prix sont obligatoires.", "error")
        return redirect(url_for("admin_dashboard"))
    try:
        price = float(price_raw)
        if price < 0 or price > 100000000:
            raise ValueError()
    except ValueError:
        flash("Prix invalide. / السعر غير صحيح.", "error")
        return redirect(url_for("admin_dashboard"))
    saved_images = []
    for image_file in image_files:
        original = secure_filename(image_file.filename)
        image_name = secrets.token_hex(8) + "_" + original
        image_file.save(UPLOAD_DIR / image_name)
        saved_images.append(image_name)
    image_name = ",".join(saved_images)
    with db() as con:
        con.execute("""INSERT INTO products
            (name_fr, name_ar, description_fr, description_ar, price, image)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (name_fr, name_ar, desc_fr, desc_ar, price, image_name))
    flash("Produit ajouté ! / تمت إضافة المنتج!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    with db() as con:
        product = con.execute("SELECT image FROM products WHERE id=?", (product_id,)).fetchone()
        con.execute("UPDATE orders SET product_id=NULL WHERE product_id=?", (product_id,))
        con.execute("DELETE FROM products WHERE id=?", (product_id,))
    if product and product["image"]:
        for image_name in product["image"].split(","):
            if image_name:
                try:
                    (UPLOAD_DIR / image_name).unlink(missing_ok=True)
                except OSError:
                    pass
    flash("Produit supprimé. / تم حذف المنتج.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    status = request.form.get("status", "Nouvelle")
    if status not in ("Nouvelle", "Confirmée", "En préparation", "Expédiée", "Livrée", "Annulée"):
        abort(400)
    with db() as con:
        con.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    flash("Statut mis à jour. / تم تحديث حالة الطلب.", "success")
    return redirect(url_for("admin_dashboard") + "#orders")

@app.route("/admin/orders/<int:order_id>/delete", methods=["POST"])
@admin_required
def delete_order(order_id):
    with db() as con:
        con.execute("DELETE FROM orders WHERE id=?", (order_id,))
    flash("Commande supprimée.", "success")
    return redirect(url_for("admin_dashboard") + "#orders")

@app.errorhandler(413)
def too_large(_error):
    flash("Image trop volumineuse (max 5 Mo). / الصورة كبيرة جدًا (الحد الأقصى 5 ميغابايت).", "error")
    return redirect(request.referrer or url_for("index"))

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
