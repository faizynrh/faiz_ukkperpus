from flask import (
    Flask,
    render_template,
    session,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta, date
import os
from flask import request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "many random bytes"


app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "FAIZ_UKKPerpus"


mysql = MySQL(app)


@app.route("/")
def home():
    return render_template("user/index.html")


@app.route("/home/buku")
def home_buku():
    faiz_cur = mysql.connection.cursor()

    faiz_cur.execute(
        """
            SELECT 
                b.BukuID, 
                b.Judul, 
                b.Penulis, 
                b.Penerbit, 
                b.TahunTerbit, 
                b.Stok,
                b.Gambar, 
                GROUP_CONCAT(DISTINCT kb.KategoriID SEPARATOR ',') AS KategoriIDs,  
                GROUP_CONCAT(DISTINCT kb.NamaKategori SEPARATOR ', ') AS Kategori,
                COALESCE(ROUND(AVG(u.Rating), 1), 0) AS RataRating,
                (SELECT COUNT(*) FROM ulasanbuku WHERE BukuID = b.BukuID) AS JumlahUlasan
            FROM 
                buku b
            LEFT JOIN 
                kategoribuku_relasi kr ON b.BukuID = kr.BukuID
            LEFT JOIN 
                kategoribuku kb ON kr.KategoriID = kb.KategoriID
            LEFT JOIN 
                ulasanbuku u ON b.BukuID = u.BukuID
            WHERE 
                b.Stok > 0
            GROUP BY 
                b.BukuID, 
                b.Judul, 
                b.Penulis, 
                b.Penerbit, 
                b.TahunTerbit, 
                b.Stok,
                b.Gambar
        """
    )
    faiz_bukudata = faiz_cur.fetchall()

    koleksi_user = []
    is_logged_in = False
    if "faiz_UserID" in session:
        is_logged_in = True
        user_id = session["faiz_UserID"]

        faiz_cur.execute(
            """
            SELECT BukuID 
            FROM koleksipribadi 
            WHERE UserID = %s
            """,
            (user_id,),
        )
        koleksi_user = [row[0] for row in faiz_cur.fetchall()]

    faiz_cur.close()

    modified_bukudata = []
    for buku in faiz_bukudata:
        buku_dict = list(buku)
        buku_dict.append(buku[0] in koleksi_user)
        modified_bukudata.append(buku_dict)

    return render_template(
        "user/buku.html", faiz_buku=modified_bukudata, is_logged_in=is_logged_in
    )


@app.route("/home/buku_saya")
def home_buku_saya():
    is_logged_in = "faiz_UserID" in session
    faiz_cur = mysql.connection.cursor()
    faiz_cur.execute(
        """
        SELECT 
            peminjaman.*, 
            buku.BukuID,
            buku.Judul, 
            buku.Penulis, 
            buku.Penerbit, 
            buku.Gambar
        FROM peminjaman 
        JOIN buku ON peminjaman.BukuID = buku.BukuID
        WHERE peminjaman.UserID = %s AND peminjaman.StatusPeminjaman = 'Dipinjam'
    """,
        (session["faiz_UserID"],),
    )
    faiz_bukudipinjam = faiz_cur.fetchall()

    faiz_cur.execute(
        """
        SELECT 
            peminjaman.*,
            buku.BukuID,
            buku.Judul, 
            buku.Penulis, 
            buku.Penerbit, 
            buku.Gambar
        FROM peminjaman 
        JOIN buku ON peminjaman.BukuID = buku.BukuID
        WHERE peminjaman.UserID = %s AND peminjaman.StatusPeminjaman = 'Tertunda'
    """,
        (session["faiz_UserID"],),
    )
    faiz_bukupending = faiz_cur.fetchall()

    faiz_cur.execute(
        """
        SELECT 
            peminjaman.*, 
            buku.BukuID,
            buku.Judul, 
            buku.Penulis, 
            buku.Penerbit, 
            buku.Gambar
        FROM peminjaman 
        JOIN buku ON peminjaman.BukuID = buku.BukuID
        WHERE peminjaman.UserID = %s AND peminjaman.StatusPeminjaman = 'Selesai'
    """,
        (session["faiz_UserID"],),
    )
    faiz_bukuselesai = faiz_cur.fetchall()

    faiz_cur.execute(
        """
            SELECT 
                koleksipribadi.*, 
                buku.BukuID,
                buku.Judul, 
                buku.Penulis, 
                buku.Penerbit, 
                buku.Gambar,
                ROUND(AVG(ulasanbuku.Rating), 1) AS RataRating,
                COUNT(ulasanbuku.Rating) AS JumlahUlasan
            FROM koleksipribadi 
            JOIN buku ON koleksipribadi.BukuID = buku.BukuID
            LEFT JOIN ulasanbuku ON buku.BukuID = ulasanbuku.BukuID
            WHERE koleksipribadi.UserID = %s
            GROUP BY 
                koleksipribadi.KoleksiID,
                buku.BukuID,
                buku.Judul, 
                buku.Penulis, 
                buku.Penerbit, 
                buku.Gambar
    """,
        (session["faiz_UserID"],),
    )
    faiz_koleksibuku = faiz_cur.fetchall()

    return render_template(
        "user/bukusaya.html",
        faiz_bukudipinjam=faiz_bukudipinjam,
        faiz_bukupending=faiz_bukupending,
        faiz_bukuselesai=faiz_bukuselesai,
        faiz_koleksibuku=faiz_koleksibuku,
        today=date.today(),
        is_logged_in=is_logged_in,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        faiz_email = request.form["email"]
        faiz_password = request.form["password"]

        try:
            faiz_cur = mysql.connection.cursor()
            faiz_cur.execute("SELECT * FROM user WHERE email = %s", (faiz_email,))
            faiz_user = faiz_cur.fetchone()
            faiz_cur.close()

            if faiz_user:

                if faiz_user[7] != "Terverifikasi":
                    flash("Akun Anda belum diverifikasi", "warning")
                    return redirect(url_for("login"))

                if check_password_hash(faiz_user[2], faiz_password):
                    session["faiz_UserID"] = faiz_user[0]
                    session["faiz_Username"] = faiz_user[1]
                    session["faiz_NamaLengkap"] = faiz_user[5]
                    session["faiz_Email"] = faiz_user[4]
                    session["faiz_Role"] = faiz_user[3]

                    if session["faiz_Role"] == "admin":
                        return redirect(url_for("admin_kelolaakun"))
                    elif session["faiz_Role"] == "petugas":
                        return redirect(url_for("admin_kelolaakun"))
                    elif session["faiz_Role"] == "peminjam":
                        return redirect(url_for("home"))
                else:
                    flash("Email atau Password Salah", "danger")
                    return redirect(url_for("login"))
            else:
                flash("Email tidak ditemukan", "danger")
                return redirect(url_for("login"))

        except Exception as e:

            flash(f"Terjadi kesalahan: {str(e)}", "danger")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        faiz_namalengkap = request.form["namalengkap"]
        faiz_username = request.form["username"]
        faiz_email = request.form["email"]
        faiz_password = request.form["password"]
        faiz_konfirmasipassword = request.form["konfirmasipassword"]
        faiz_alamat = request.form["alamat"]

        if faiz_password != faiz_konfirmasipassword:
            flash("Password Tidak Sesuai", "danger")
            return redirect(url_for("signup"))

        try:
            faiz_cur = mysql.connection.cursor()

            faiz_cur.execute(
                "SELECT * FROM user WHERE Email = %s OR Username = %s",
                (faiz_email, faiz_username),
            )
            faiz_existing_user = faiz_cur.fetchone()

            if faiz_existing_user:
                flash("Email atau Username sudah terdaftar!", "danger")
                faiz_cur.close()
                return redirect(url_for("signup"))

            faiz_hashed_password = generate_password_hash(faiz_password)

            faiz_cur.execute(
                """
                INSERT INTO user 
                (NamaLengkap, Username, Password, Role, Email, Alamat, Status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    faiz_namalengkap,
                    faiz_username,
                    faiz_hashed_password,
                    "peminjam",
                    faiz_email,
                    faiz_alamat,
                    "Pending",
                ),
            )

            mysql.connection.commit()

            faiz_cur.close()

            flash(
                "Pendaftaran berhasil! Silakan tunggu konfirmasi dari admin", "success"
            )
            return redirect(url_for("login"))

        except Exception as e:
            flash(f"Terjadi kesalahan: {str(e)}", "danger")
            return redirect(url_for("signup"))

    return render_template("signup.html")


@app.route("/admin/kelola_akun")
def admin_kelolaakun():
    faiz_cur = mysql.connection.cursor()

    faiz_cur.execute("SELECT * FROM user")
    faiz_datauser = faiz_cur.fetchall()

    faiz_cur.close()

    return render_template(
        "niceadmin/kelola_akun.html",
        faiz_user=faiz_datauser,
        faiz_activepage="kelola_akun",
    )


@app.route("/tambah_akun", methods=["POST"])
def tambah_akun():
    faiz_username = request.form["username"]
    faiz_email = request.form["email"]
    faiz_password = request.form["password"]
    faiz_confirm_password = request.form["confirmPassword"]
    faiz_role = request.form["role"]
    faiz_nama_lengkap = request.form["nama_lengkap"]
    faiz_alamat = request.form["alamat"]

    if faiz_password != faiz_confirm_password:
        flash("Konfirmasi password tidak sama.", "danger")
        return redirect(url_for("admin_kelolaakun"))

    faiz_cur = mysql.connection.cursor()

    faiz_cur.execute("SELECT * FROM user WHERE email = %s", (faiz_email,))
    faiz_email_ada = faiz_cur.fetchone()

    faiz_cur.execute("SELECT * FROM user WHERE Username = %s", (faiz_username,))
    faiz_username_ada = faiz_cur.fetchone()

    if faiz_email_ada:
        faiz_cur.close()
        flash("Email sudah terdaftar. Silakan gunakan email lain.", "danger")
        return redirect(url_for("admin_kelolaakun"))

    if faiz_username_ada:
        faiz_cur.close()
        flash("Username sudah terdaftar. Silakan gunakan username lain.", "danger")
        return redirect(url_for("admin_kelolaakun"))

    faiz_hashed_password = generate_password_hash(faiz_password)

    faiz_cur.execute(
        """INSERT INTO user (Username, Password, Role, Email, NamaLengkap, Alamat, Status) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (
            faiz_username,
            faiz_hashed_password,
            faiz_role,
            faiz_email,
            faiz_nama_lengkap,
            faiz_alamat,
            "Terverifikasi",
        ),
    )

    mysql.connection.commit()
    faiz_cur.close()

    flash("Berhasil menambahkan akun!", "success")

    return redirect(url_for("admin_kelolaakun"))


@app.route("/edit_akun/<int:akun_id>", methods=["POST"])
def edit_akun(akun_id):
    faiz_username = request.form["username"]
    faiz_email = request.form["email"]
    faiz_role = request.form["role"]
    faiz_nama_lengkap = request.form["nama_lengkap"]
    faiz_alamat = request.form["alamat"]

    faiz_cur = mysql.connection.cursor()

    faiz_cur.execute(
        """
        UPDATE user SET Username=%s, Role=%s, Email=%s, NamaLengkap=%s, Alamat=%s
                    WHERE UserID=%s""",
        (faiz_username, faiz_role, faiz_email, faiz_nama_lengkap, faiz_alamat, akun_id),
    )

    mysql.connection.commit()

    faiz_cur.close()

    flash("Data berhasil diubah!", "success")

    return redirect(url_for("admin_kelolaakun"))


@app.route("/hapus_akun/<int:akun_id>", methods=["POST"])
def hapus_akun(akun_id):
    faiz_cur = mysql.connection.cursor()
    faiz_cur.execute("DELETE FROM ulasanbuku WHERE UserID = %s", (akun_id,))
    faiz_cur.execute("DELETE FROM koleksipribadi WHERE UserID = %s", (akun_id,))
    faiz_cur.execute("DELETE FROM peminjaman WHERE UserID = %s", (akun_id,))
    faiz_cur.execute("DELETE FROM user WHERE UserID = %s", (akun_id,))

    mysql.connection.commit()

    faiz_cur.close()
    flash("Akun berhasil dihapus!", "success")

    return redirect(url_for("admin_kelolaakun"))


@app.route("/verifikasi_akun/<int:akun_id>", methods=["POST"])
def verifikasi_akun(akun_id):
    try:
        faiz_cursor = mysql.connection.cursor()
        faiz_cursor.execute(
            "UPDATE user SET Status = 'Terverifikasi' WHERE UserID = %s", (akun_id,)
        )
        mysql.connection.commit()
        faiz_cursor.close()

        flash("Akun berhasil diverifikasi", "success")
    except Exception as faiz_error:
        print(f"Error verifikasi akun: {str(faiz_error)}")
        flash(f"Gagal memverifikasi akun: {str(faiz_error)}", "danger")

    return redirect(url_for("admin_kelolaakun"))


@app.route("/tolak_akun/<int:akun_id>", methods=["POST"])
def tolak_akun(akun_id):
    try:
        faiz_cursor = mysql.connection.cursor()

        faiz_cursor.execute("DELETE FROM user WHERE UserID = %s", (akun_id,))

        mysql.connection.commit()
        faiz_cursor.close()

        flash("Akun berhasil ditolak dan dihapus", "success")
    except Exception as faiz_error:
        print(f"Error tolak akun: {str(faiz_error)}")
        flash(f"Gagal menolak akun: {str(faiz_error)}", "danger")

    return redirect(url_for("admin_kelolaakun"))


@app.route("/admin/kategori_buku")
def admin_kategoribuku():
    faiz_cur = mysql.connection.cursor()

    faiz_cur.execute("SELECT * FROM kategoribuku")

    faiz_datakategori = faiz_cur.fetchall()

    faiz_cur.close()

    return render_template(
        "niceadmin/kategori_buku.html",
        faiz_kategori=faiz_datakategori,
        active_page="kategori_buku",
    )


@app.route("/tambah_kategori", methods=["POST"])
def tambah_kategori():
    faiz_nama_kategori = request.form["nama_kategori"]

    faiz_cur = mysql.connection.cursor()
    # Ambil UserID dari session
    user_id = session.get("faiz_UserID")

    faiz_cur.execute(
        """
        INSERT INTO kategoribuku (NamaKategori)
        VALUES (%s)
        """,
        (faiz_nama_kategori,),
    )

    mysql.connection.commit()

    faiz_cur.close()
    flash("Berhasil menambah kategori!", "success")

    return redirect(url_for("admin_kategoribuku"))


@app.route("/edit_kategori/<int:kategori_id>", methods=["POST"])
def edit_kategori(kategori_id):

    faiz_nama_kategori = request.form["nama_kategori"]

    faiz_cur = mysql.connection.cursor()

    faiz_cur.execute(
        "UPDATE kategoribuku SET NamaKategori = %s WHERE KategoriID = %s",
        (faiz_nama_kategori, kategori_id),
    )

    mysql.connection.commit()
    faiz_cur.close()

    flash("Kategori berhasil diubah!", "success")
    return redirect(url_for("admin_kategoribuku"))


@app.route("/hapus_kategori/<int:kategori_id>", methods=["POST"])
def hapus_kategori(kategori_id):
    faiz_user_id = session.get("id")
    faiz_cur = mysql.connection.cursor()
    faiz_cur.execute(
        "DELETE FROM kategoribuku_relasi WHERE KategoriID = %s", (kategori_id,)
    )
    faiz_cur.execute("DELETE FROM kategoribuku WHERE KategoriID = %s", (kategori_id,))

    mysql.connection.commit()
    faiz_cur.close()

    flash(f"Kategori berhasil dihapus!", "success")
    return redirect(url_for("admin_kategoribuku"))


@app.route("/admin/buku")
def admin_buku():
    faiz_cur = mysql.connection.cursor()

    faiz_cur.execute(
        """
        SELECT 
            b.BukuID, 
            b.Judul, 
            b.Penulis, 
            b.Penerbit, 
            b.TahunTerbit, 
            b.Stok,
            b.Gambar, 
            GROUP_CONCAT(kb.KategoriID SEPARATOR ',') AS KategoriIDs,  
            GROUP_CONCAT(kb.NamaKategori SEPARATOR ', ') AS Kategori
        FROM 
            buku b
        LEFT JOIN 
            kategoribuku_relasi kr ON b.BukuID = kr.BukuID
        LEFT JOIN 
            kategoribuku kb ON kr.KategoriID = kb.KategoriID
        GROUP BY 
            b.BukuID, 
            b.Judul, 
            b.Penulis, 
            b.Penerbit, 
            b.TahunTerbit, 
            b.Gambar
    """
    )
    faiz_databuku = faiz_cur.fetchall()

    faiz_cur.execute("SELECT * FROM kategoribuku")
    faiz_datakategori = faiz_cur.fetchall()

    faiz_cur.close()

    return render_template(
        "niceadmin/buku.html",
        faiz_buku=faiz_databuku,
        faiz_kategori=faiz_datakategori,
        active_page="buku",
    )


@app.route("/tambah_buku", methods=["POST"])
def tambah_buku():
    try:
        faiz_judul = request.form["judul"]
        faiz_penulis = request.form["penulis"]
        faiz_penerbit = request.form["penerbit"]
        faiz_tahun_terbit = request.form["tahun_terbit"]
        faiz_stok = request.form["stok"]

        faiz_kategori_terpilih = request.form.getlist("kategori[]")

        if "gambar" not in request.files:
            flash("Tidak ada file gambar yang diunggah", "danger")
            return redirect(url_for("admin_buku"))

        faiz_gambar = request.files["gambar"]

        if faiz_gambar:
            faiz_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            faiz_file_ext = os.path.splitext(faiz_gambar.filename)[1]
            faiz_nama_file = secure_filename(
                f"{faiz_judul}_{faiz_timestamp}{faiz_file_ext}"
            )

            faiz_file_path = os.path.join(app.root_path, UPLOAD_FOLDER, faiz_nama_file)

            faiz_gambar.save(faiz_file_path)

            faiz_path_database = f"sampulbuku/{faiz_nama_file}"

            faiz_cursor = mysql.connection.cursor()

            faiz_cursor.execute(
                """
                INSERT INTO buku 
                (Judul, Penulis, Penerbit, TahunTerbit, Stok, Gambar) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    faiz_judul,
                    faiz_penulis,
                    faiz_penerbit,
                    faiz_tahun_terbit,
                    faiz_stok,
                    faiz_path_database,
                ),
            )

            faiz_buku_id = faiz_cursor.lastrowid

            for faiz_kategori_id in faiz_kategori_terpilih:
                faiz_cursor.execute(
                    """
                    INSERT INTO kategoribuku_relasi 
                    (BukuID, KategoriID) 
                    VALUES (%s, %s)
                    """,
                    (faiz_buku_id, faiz_kategori_id),
                )

            mysql.connection.commit()
            faiz_cursor.close()

            flash("Buku berhasil ditambahkan", "success")
            return redirect(url_for("admin_buku"))

    except Exception as e:
        flash(f"Terjadi kesalahan: {str(e)}", "danger")
        return redirect(url_for("admin_buku"))


@app.route("/hapus_buku/<int:id>", methods=["POST"])
def hapus_buku(id):
    try:
        faiz_cursor = mysql.connection.cursor()

        faiz_cursor.execute("DELETE FROM kategoribuku_relasi WHERE BukuID = %s", (id,))
        faiz_cursor.execute("DELETE FROM peminjaman WHERE BukuID = %s", (id,))
        faiz_cursor.execute("DELETE FROM koleksipribadi WHERE BukuID = %s", (id,))
        faiz_cursor.execute("DELETE FROM ulasanbuku WHERE BukuID = %s", (id,))

        faiz_cursor.execute("SELECT Gambar FROM buku WHERE BukuID = %s", (id,))
        faiz_sampul = faiz_cursor.fetchone()

        faiz_cursor.execute("DELETE FROM buku WHERE BukuID = %s", (id,))

        mysql.connection.commit()

        if faiz_sampul and faiz_sampul[0]:
            faiz_file_path = os.path.join(app.root_path, faiz_sampul[0])
            if os.path.exists(faiz_file_path):
                os.remove(faiz_file_path)

        faiz_cursor.close()
        flash("Buku berhasil dihapus", "success")
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Gagal menghapus buku: {str(e)}", "danger")

    return redirect(url_for("admin_buku"))


@app.route("/edit_buku/<int:id>", methods=["POST"])
def edit_buku(id):
    try:
        faiz_judul = request.form["judul"]
        faiz_penulis = request.form["penulis"]
        faiz_penerbit = request.form["penerbit"]
        faiz_tahun_terbit = request.form["tahun_terbit"]
        faiz_stok = request.form["stok"]
        faiz_kategori_terpilih = request.form.getlist("kategori[]")

        if "gambar" in request.files and request.files["gambar"].filename != "":
            faiz_gambar = request.files["gambar"]
            faiz_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            faiz_file_ext = os.path.splitext(faiz_gambar.filename)[1]
            faiz_nama_file = secure_filename(
                f"{faiz_judul}_{faiz_timestamp}{faiz_file_ext}"
            )
            faiz_file_path = os.path.join(app.root_path, UPLOAD_FOLDER, faiz_nama_file)
            faiz_gambar.save(faiz_file_path)
            faiz_path_database = f"sampulbuku/{faiz_nama_file}"
        else:
            faiz_path_database = request.form["sampul_lama"]

        faiz_cursor = mysql.connection.cursor()

        faiz_cursor.execute(
            """
            UPDATE buku 
            SET Judul = %s, Penulis = %s, Penerbit = %s, TahunTerbit = %s, Stok = %s, Gambar = %s
            WHERE BukuID = %s
            """,
            (
                faiz_judul,
                faiz_penulis,
                faiz_penerbit,
                faiz_tahun_terbit,
                faiz_stok,
                faiz_path_database,
                id,
            ),
        )

        faiz_cursor.execute("DELETE FROM kategoribuku_relasi WHERE BukuID = %s", (id,))

        for faiz_kategori_id in faiz_kategori_terpilih:
            faiz_cursor.execute(
                """
                INSERT INTO kategoribuku_relasi 
                (BukuID, KategoriID) 
                VALUES (%s, %s)
                """,
                (id, faiz_kategori_id),
            )

        mysql.connection.commit()
        faiz_cursor.close()

        flash("Buku berhasil diperbarui", "success")
        return redirect(url_for("admin_buku"))

    except Exception as e:
        flash(f"Terjadi kesalahan: {str(e)}", "danger")
        return redirect(url_for("admin_buku"))


@app.route("/admin/peminjaman")
def admin_peminjaman():
    faiz_cur = mysql.connection.cursor()

    faiz_cur.execute(
        """
            SELECT DISTINCT 
                p.PeminjamanID, 
                u.UserID,
                u.NamaLengkap, 
                b.BukuID,
                b.Judul,
                p.TanggalPeminjaman,
                p.TanggalPengembalian,
                pg.TanggalDikembalikan,
                pg.Denda,
                pg.NilaiDenda,
                p.StatusPeminjaman
            FROM 
                peminjaman p
            JOIN 
                user u ON p.UserID = u.UserID
            JOIN 
                buku b ON p.BukuID = b.BukuID
            LEFT JOIN 
                pengembalian pg ON p.PeminjamanID = pg.PeminjamanID
                    """
    )
    faiz_datapeminjaman = faiz_cur.fetchall()

    faiz_cur.execute(
        """
            SELECT u.UserID, u.NamaLengkap
            FROM user u
            WHERE
                u.role = 'peminjam'
                AND u.Status = 'Terverifikasi'
                AND (
                    (SELECT COUNT(*)
                     FROM peminjaman p
                     WHERE p.UserID = u.UserID
                     AND p.StatusPeminjaman != 'Dikembalikan') < 3
                )
        """
    )
    faiz_datapeminjam = faiz_cur.fetchall()

    faiz_cur.execute(
        """
            SELECT b.BukuID, b.Judul
            FROM buku b
            WHERE Stok > 0
        """
    )
    faiz_databuku = faiz_cur.fetchall()

    faiz_cur.close()

    return render_template(
        "niceadmin/peminjaman.html",
        faiz_peminjaman=faiz_datapeminjaman,
        faiz_peminjam=faiz_datapeminjam,
        faiz_buku=faiz_databuku,
        active_page="peminjaman",
    )


@app.route("/pengembalian/<int:id>", methods=["POST"])
def pengembalian(id):
    faiz_cur = mysql.connection.cursor()

    faiz_tanggal_kembali = datetime.now().strftime("%Y-%m-%d")

    # Ambil data buku yang dipinjam
    faiz_cur.execute(
        "SELECT BukuID FROM peminjaman WHERE PeminjamanID = %s",
        (id,),
    )
    buku_id = faiz_cur.fetchone()[0]

    faiz_cur.execute(
        "SELECT TanggalPengembalian FROM peminjaman WHERE PeminjamanID = %s",
        (id,),
    )
    rencana_kembali = faiz_cur.fetchone()[0]

    denda = request.form.get("jenisDenda")
    nilai_denda = request.form.get("nilaiDenda")

    denda_tambahan = request.form.get("jenisDendaTambahan")
    nilai_denda_tambahan = request.form.get("nilaiDendaTambahan")

    # Proses validasi input seperti sebelumnya...
    # (kode yang Anda miliki sebelumnya)

    # Tambahkan logika untuk penambahan stok
    tambah_stok = True  # Default adalah tambah stok

    # Cek jika ada denda rusak/hilang
    if (denda and denda.lower() in ["rusak", "hilang"]) or (
        denda_tambahan and denda_tambahan.lower() in ["rusak", "hilang"]
    ):
        tambah_stok = False

    # Proses insert pengembalian seperti sebelumnya
    if (denda and nilai_denda) and (denda_tambahan and nilai_denda_tambahan):
        faiz_cur.execute(
            """
            INSERT INTO pengembalian (
                PeminjamanID, 
                TanggalDikembalikan, 
                Denda,
                NilaiDenda
            ) VALUES (%s, %s, %s, %s)
            """,
            (id, faiz_tanggal_kembali, denda, nilai_denda),
        )

        faiz_cur.execute(
            """
            INSERT INTO pengembalian (
                PeminjamanID, 
                TanggalDikembalikan, 
                Denda,
                NilaiDenda
            ) VALUES (%s, %s, %s, %s)
            """,
            (id, faiz_tanggal_kembali, denda_tambahan, nilai_denda_tambahan),
        )
    elif denda and nilai_denda:
        faiz_cur.execute(
            """
            INSERT INTO pengembalian (
                PeminjamanID, 
                TanggalDikembalikan, 
                Denda,
                NilaiDenda
            ) VALUES (%s, %s, %s, %s)
            """,
            (id, faiz_tanggal_kembali, denda, nilai_denda),
        )

    # Update status peminjaman
    faiz_cur.execute(
        """
        UPDATE peminjaman 
        SET StatusPeminjaman = 'Selesai'
        WHERE PeminjamanID = %s
        """,
        (id,),
    )

    # Tambahkan stok buku jika tidak ada denda rusak/hilang
    if tambah_stok:
        faiz_cur.execute(
            """
            UPDATE buku 
            SET Stok = Stok + 1 
            WHERE BukuID = %s
            """,
            (buku_id,),
        )

    mysql.connection.commit()
    faiz_cur.close()

    flash("Buku berhasil dikembalikan", "success")
    return redirect(url_for("admin_peminjaman"))


@app.route("/peminjaman/<int:id>", methods=["POST"])
def peminjaman(id):
    faiz_cur = mysql.connection.cursor()
    faiz_bukuid = request.form.get("bukuid")
    print(f"BukuID: {faiz_bukuid}")

    faiz_cur.execute(
        """
        UPDATE peminjaman 
        SET StatusPeminjaman = 'Dipinjam'
        WHERE PeminjamanID = %s
        """,
        (id,),
    )

    faiz_cur.execute(
        """
        UPDATE buku 
        SET Stok = Stok - 1
        WHERE BukuID = %s
        """,
        (faiz_bukuid,),
    )

    mysql.connection.commit()
    faiz_cur.close()

    flash("Buku berhasil dipinjam", "success")
    return redirect(url_for("admin_peminjaman"))


@app.route("/tambah_peminjaman", methods=["POST"])
def tambah_peminjaman():
    faiz_nama_peminjam = request.form["nama_peminjam"]
    faiz_buku = request.form["buku"]
    faiz_tanggal_peminjaman = request.form["tanggal_peminjaman"]
    faiz_tanggal_pengembalian = request.form["tanggal_pengembalian"]
    faiz_cur = mysql.connection.cursor()

    faiz_cur.execute(
        """
        INSERT INTO peminjaman (UserID, BukuID, TanggalPeminjaman, TanggalPengembalian, StatusPeminjaman)
        VALUES (%s, %s, %s, %s, 'Dipinjam')
        """,
        (
            faiz_nama_peminjam,
            faiz_buku,
            faiz_tanggal_peminjaman,
            faiz_tanggal_pengembalian,
        ),
    )

    faiz_cur.execute(
        """
        UPDATE buku 
        SET Stok = Stok - 1
        WHERE BukuID = %s
        """,
        (faiz_buku,),
    )

    mysql.connection.commit()

    faiz_cur.close()
    flash("Berhasil menambah Peminjaman", "success")

    return redirect(url_for("admin_peminjaman"))


# @app.route("/")
# def index():
#     faiz_cursor = mysql.connection.cursor()
#     faiz_cursor.execute("SELECT BukuID, Judul, Gambar FROM buku")
#     faiz_bukulist = faiz_cursor.fetchall()
#     faiz_cursor.close()

#     return render_template("index.html", faiz_bukulist=faiz_bukulist)


@app.route("/user_peminjaman", methods=["POST"])
def user_peminjaman():
    try:
        userid = session.get("faiz_UserID")
        bukuid = request.form.get("bukuid")
        tanggal_peminjaman = datetime.now().date()
        tanggal_pengembalian = tanggal_peminjaman + timedelta(days=7)
        status = "Tertunda"

        cur = mysql.connection.cursor()

        cur.execute(
            """
            SELECT COUNT(*) as jumlah_peminjaman_buku 
            FROM peminjaman 
            WHERE UserID = %s 
            AND BukuID = %s
            AND (StatusPeminjaman = 'Tertunda' OR StatusPeminjaman = 'Dipinjam')
            """,
            (userid, bukuid),
        )
        result_buku_sama = cur.fetchone()
        jumlah_peminjaman_buku = result_buku_sama[0]

        if jumlah_peminjaman_buku > 0:
            flash("Anda sudah meminjam buku ini", "error")
            return redirect(url_for("home_buku"))

        cur.execute(
            """
            SELECT COUNT(*) as jumlah_peminjaman 
            FROM peminjaman 
            WHERE UserID = %s 
            AND (StatusPeminjaman = 'Tertunda' OR StatusPeminjaman = 'Dipinjam')
            """,
            (userid,),
        )

        result = cur.fetchone()
        jumlah_peminjaman = result[0]

        if jumlah_peminjaman >= 3:
            flash("Anda sudah mencapai batas maksimal peminjaman (3 buku)", "error")
            return redirect(url_for("home_buku"))

        cur.execute(
            """
            SELECT Stok FROM buku WHERE BukuID = %s
            """,
            (bukuid,),
        )
        stok_result = cur.fetchone()

        if stok_result[0] <= 0:
            flash("Buku tidak tersedia", "error")
            return redirect(url_for("home_buku"))

        cur.execute(
            """
            INSERT INTO peminjaman 
            (UserID, BukuID, TanggalPeminjaman, TanggalPengembalian, StatusPeminjaman) 
            VALUES (%s, %s, %s, %s, %s)
            """,
            (userid, bukuid, tanggal_peminjaman, tanggal_pengembalian, status),
        )

        cur.execute(
            """
            UPDATE buku 
            SET Stok = Stok - 1
            WHERE BukuID = %s
            """,
            (bukuid,),
        )

        mysql.connection.commit()
        cur.close()

        flash("Buku berhasil dipinjam", "success")
        return redirect(url_for("home_buku"))

    except Exception as e:
        mysql.connection.rollback()
        print(f"Error: {str(e)}")
        flash("Gagal meminjam buku. Silahkan coba lagi.", "error")
        return redirect(url_for("home_buku"))


@app.route("/kembalikan_buku", methods=["POST"])
def kembalikan_buku():
    try:
        # Ambil data dari session dan form
        userid = session.get("faiz_UserID")
        bukuid = request.form.get("id_buku")

        print(f"UserID: {userid}")
        print(f"BukuID: {bukuid}")

        # Validasi input
        if not bukuid:
            flash("Buku tidak valid", "error")
            return redirect(url_for("home_buku_saya"))

        # Buat koneksi cursor
        cur = mysql.connection.cursor()

        # Cek apakah buku benar-benar dipinjam
        cur.execute(
            """
            SELECT StatusPeminjaman FROM peminjaman
            WHERE UserID = %s AND BukuID = %s AND StatusPeminjaman = 'Dipinjam'
            """,
            (userid, bukuid),
        )
        peminjaman = cur.fetchone()

        if not peminjaman:
            flash("Buku tidak ditemukan atau tidak sedang dipinjam", "error")
            return redirect(url_for("home_buku_saya"))

        # Update status peminjaman menjadi pending pengembalian
        cur.execute(
            """
            UPDATE peminjaman
            SET StatusPeminjaman = 'PendingPengembalian'
            WHERE UserID = %s AND BukuID = %s AND StatusPeminjaman = 'Dipinjam'
            """,
            (userid, bukuid),
        )

        # Commit transaksi
        mysql.connection.commit()

        # Tutup cursor
        cur.close()

        # Berikan feedback
        flash("Buku sedang diproses untuk pengembalian", "success")
        return redirect(url_for("home_buku_saya"))

    except Exception as e:
        # Rollback jika terjadi kesalahan
        mysql.connection.rollback()

        # Catat error
        print(f"Error: {str(e)}")

        # Berikan feedback error
        flash("Gagal memproses pengembalian buku. Silahkan coba lagi.", "error")
        return redirect(url_for("home_buku_saya"))


@app.route("/tambah_koleksi_pribadi/<int:buku_id>", methods=["POST"])
def tambah_koleksi_pribadi(buku_id):
    if "faiz_UserID" not in session:
        return (
            jsonify({"status": "error", "message": "Silahkan login terlebih dahulu"}),
            401,
        )

    user_id = session["faiz_UserID"]

    try:
        # Cek apakah buku valid
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM buku WHERE BukuID = %s", (buku_id,))
        buku_exists = cur.fetchone()[0]

        if buku_exists == 0:
            cur.close()
            return jsonify({"status": "error", "message": "Buku tidak ditemukan"}), 404

        # Cek apakah buku sudah ada di koleksi
        cur.execute(
            """
            SELECT COUNT(*) FROM koleksipribadi 
            WHERE UserID = %s AND BukuID = %s
        """,
            (user_id, buku_id),
        )

        existing = cur.fetchone()[0]

        if existing > 0:
            cur.close()
            return (
                jsonify(
                    {"status": "error", "message": "Buku sudah ada di koleksi pribadi"}
                ),
                400,
            )

        # Tambahkan ke koleksi pribadi
        cur.execute(
            """
            INSERT INTO koleksipribadi (UserID, BukuID) 
            VALUES (%s, %s)
        """,
            (user_id, buku_id),
        )

        mysql.connection.commit()
        cur.close()

        return redirect(url_for("home_buku_saya"))

    except Exception as e:
        print(f"Error menambah koleksi pribadi: {e}")
        return jsonify({"status": "error", "message": "Terjadi kesalahan sistem"}), 500


@app.route("/hapus_koleksi_pribadi/<int:buku_id>", methods=["POST"])
def hapus_koleksi_pribadi(buku_id):
    if "faiz_UserID" not in session:
        flash("Anda harus login terlebih dahulu", "danger")
        return redirect(url_for("login"))

    try:
        user_id = session["faiz_UserID"]
        faiz_cur = mysql.connection.cursor()

        faiz_cur.execute(
            "DELETE FROM koleksipribadi WHERE UserID = %s AND BukuID = %s",
            (user_id, buku_id),
        )
        mysql.connection.commit()

        faiz_cur.close()

        flash("Buku berhasil dihapus dari koleksi pribadi", "success")
        return redirect(url_for("home_buku_saya"))

    except Exception as e:
        mysql.connection.rollback()
        flash(f"Gagal menghapus buku: {str(e)}", "danger")
        return redirect(url_for("home_buku"))


@app.route("/user/ulasanbuku/<int:buku_id>")
def user_ulasanbuku(buku_id):
    cur = mysql.connection.cursor()

    try:
        # Ambil data buku
        cur.execute("SELECT * FROM buku WHERE BukuID = %s", (buku_id,))
        buku_data = cur.fetchone()

        # Ambil rata-rata rating dan jumlah ulasan
        cur.execute(
            """
            SELECT 
                COALESCE(AVG(Rating), 0) as rata_rating, 
                COUNT(*) as jumlah_ulasan
            FROM 
                ulasanbuku
            WHERE 
                BukuID = %s
            """,
            (buku_id,),
        )
        rating_data = cur.fetchone()

        # Ambil ulasan buku
        cur.execute(
            """
            SELECT 
                u.*, 
                a.NamaLengkap 
            FROM 
                ulasanbuku u
            JOIN 
                user a ON u.UserID = a.UserID
            WHERE 
                u.BukuID = %s
            ORDER BY u.UlasanID DESC
            """,
            (buku_id,),
        )
        ulasan_data = cur.fetchall()

        # Cek apakah user sudah memberikan ulasan
        user_id = session.get("faiz_UserID")
        cur.execute(
            """
            SELECT 
                u.*, 
                a.NamaLengkap 
            FROM 
                ulasanbuku u
            JOIN 
                user a ON u.UserID = a.UserID
            WHERE 
                u.BukuID = %s AND u.UserID = %s
            """,
            (buku_id, user_id),
        )
        user_ulasan = cur.fetchone()  # Ambil ulasan dari user jika ada

        # Tutup cursor
        cur.close()

        # Render template dengan data yang diambil
        return render_template(
            "user/ulasanbuku.html",
            ulasan=ulasan_data,
            buku=buku_data,
            rata_rating=rating_data[0],
            jumlah_ulasan=rating_data[1],
            user_ulasan=user_ulasan,  # Tambahkan ulasan user
            active_page="buku",
        )

    except Exception as e:
        print(f"Error dalam user_ulasanbuku: {e}")
        import traceback

        traceback.print_exc()
        flash(f"Terjadi kesalahan: {e}", "danger")
        return redirect(url_for("home_buku_saya"))

    finally:
        cur.close()


@app.route("/user/edit_ulasan", methods=["POST"])
def edit_ulasan():
    if "faiz_UserID" not in session:
        flash("Anda harus login terlebih dahulu.", "danger")
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    try:
        # Ambil data dari form
        rating = request.form["rating"]
        ulasan_text = request.form["ulasan"]
        buku_id = request.form.get("buku_id")  # Tambahkan input tersembunyi di form
        # Cari ulasan milik user untuk buku ini
        user_id = session["faiz_UserID"]

        cur.execute(
            """
            UPDATE ulasanbuku 
            SET Rating = %s, Ulasan = %s, Tanggal = NOW()
            WHERE BukuID = %s AND UserID = %s
            """,
            (rating, ulasan_text, buku_id, user_id),
        )

        mysql.connection.commit()
        flash("Ulasan berhasil diperbarui!", "success")
    except Exception as e:
        mysql.connection.rollback()
        print(f"Error dalam edit_ulasan: {e}")
        flash("Terjadi kesalahan saat memperbarui ulasan.", "danger")
    finally:
        cur.close()

    return redirect(url_for("user_ulasanbuku", buku_id=buku_id))


@app.route("/user/hapus_ulasan", methods=["POST"])
def hapus_ulasan():
    if "faiz_UserID" not in session:
        flash("Anda harus login terlebih dahulu.", "danger")
        return redirect(url_for("login"))

    cur = mysql.connection.cursor()

    try:
        buku_id = request.form.get("buku_id")  # Tambahkan input tersembunyi di form
        user_id = session["faiz_UserID"]

        cur.execute(
            """
            DELETE FROM ulasanbuku 
            WHERE BukuID = %s AND UserID = %s
            """,
            (buku_id, user_id),
        )

        mysql.connection.commit()
        flash("Ulasan berhasil dihapus!", "success")
    except Exception as e:
        mysql.connection.rollback()
        print(f"Error dalam hapus_ulasan: {e}")
        flash("Terjadi kesalahan saat menghapus ulasan.", "danger")
    finally:
        cur.close()

    return redirect(url_for("user_ulasanbuku", buku_id=buku_id))


@app.route("/admin/laporanpeminjaman", methods=["GET"])
def laporan_peminjaman():
    cur = mysql.connection.cursor()

    cur.execute(
        """
    SELECT 
        u.NamaLengkap,
        b.Judul AS JudulBuku,
        p.TanggalPeminjaman,
        p.TanggalPengembalian,
        COALESCE(pg.TanggalDikembalikan, '-') AS TanggalDikembalikan,
        p.StatusPeminjaman,
        COALESCE(pg.Denda, '-') AS Denda,
        COALESCE(pg.NilaiDenda, '-') AS NilaiDenda
    FROM 
        peminjaman p
    JOIN 
        user u ON p.UserID = u.UserID
    JOIN 
        buku b ON p.BukuID = b.BukuID
    LEFT JOIN 
        pengembalian pg ON p.PeminjamanID = pg.PeminjamanID
    ORDER BY 
        p.TanggalPeminjaman DESC
    """
    )
    detail_peminjaman = cur.fetchall()

    return render_template(
        "niceadmin/laporanpeminjaman.html",
        detail_peminjaman=detail_peminjaman,
    )


@app.route("/admin/laporanbuku", methods=["GET"])
def laporan_buku():
    cur = mysql.connection.cursor()

    cur.execute(
        """
            SELECT 
                b.BukuID, 
                b.Judul, 
                b.Penulis, 
                b.Penerbit, 
                b.TahunTerbit, 
                GROUP_CONCAT(DISTINCT kb.NamaKategori SEPARATOR ', ') AS Kategori,
                GROUP_CONCAT(DISTINCT kb.KategoriID SEPARATOR ',') AS KategoriIDs,
                COUNT(DISTINCT CASE WHEN p.Denda = 'hilang' THEN p.PeminjamanID END) AS JumlahHilang,
                COUNT(DISTINCT CASE WHEN p.Denda = 'rusak' THEN p.PeminjamanID END) AS JumlahRusak
            FROM 
                buku b
            LEFT JOIN 
                kategoribuku_relasi kr ON b.BukuID = kr.BukuID
            LEFT JOIN 
                kategoribuku kb ON kr.KategoriID = kb.KategoriID
            LEFT JOIN 
                peminjaman pm ON b.BukuID = pm.BukuID
            LEFT JOIN 
                pengembalian p ON pm.PeminjamanID = p.PeminjamanID
            GROUP BY 
                b.BukuID, 
                b.Judul, 
                b.Penulis, 
                b.Penerbit, 
                b.TahunTerbit
            ORDER BY 
                b.BukuID;
    """
    )
    laporan_buku = cur.fetchall()

    return render_template(
        "niceadmin/laporanbuku.html",
        laporan_buku=laporan_buku,
    )


@app.route("/admin/laporanbuku/print", methods=["GET"])
def print_laporan_buku():
    cur = mysql.connection.cursor()

    cur.execute(
        """
            SELECT 
                b.BukuID, 
                b.Judul, 
                b.Penulis, 
                b.Penerbit, 
                b.TahunTerbit, 
                GROUP_CONCAT(DISTINCT kb.NamaKategori SEPARATOR ', ') AS Kategori,
                GROUP_CONCAT(DISTINCT kb.KategoriID SEPARATOR ',') AS KategoriIDs,
                COUNT(DISTINCT CASE WHEN p.Denda = 'hilang' THEN p.PeminjamanID END) AS JumlahHilang,
                COUNT(DISTINCT CASE WHEN p.Denda = 'rusak' THEN p.PeminjamanID END) AS JumlahRusak
            FROM 
                buku b
            LEFT JOIN 
                kategoribuku_relasi kr ON b.BukuID = kr.BukuID
            LEFT JOIN 
                kategoribuku kb ON kr.KategoriID = kb.KategoriID
            LEFT JOIN 
                peminjaman pm ON b.BukuID = pm.BukuID
            LEFT JOIN 
                pengembalian p ON pm.PeminjamanID = p.PeminjamanID
            GROUP BY 
                b.BukuID, 
                b.Judul, 
                b.Penulis, 
                b.Penerbit, 
                b.TahunTerbit
            ORDER BY 
                b.BukuID;
    """
    )
    laporan_buku = cur.fetchall()

    return render_template(
        "laporan/laporanbukuhilang.html",
        laporan_buku=laporan_buku,
        now=datetime.now,
    )


@app.route("/print/laporanpeminjaman", methods=["GET"])
def print_laporan_peminjaman():
    cur = mysql.connection.cursor()

    cur.execute(
        """
    SELECT 
        u.NamaLengkap,
        b.Judul AS JudulBuku,
        p.TanggalPeminjaman,
        p.TanggalPengembalian,
        COALESCE(pg.TanggalDikembalikan, '-') AS TanggalDikembalikan,
        p.StatusPeminjaman,
        COALESCE(pg.Denda, '-') AS Denda,
        COALESCE(pg.NilaiDenda, '-') AS NilaiDenda
    FROM 
        peminjaman p
    JOIN 
        user u ON p.UserID = u.UserID
    JOIN 
        buku b ON p.BukuID = b.BukuID
    LEFT JOIN 
        pengembalian pg ON p.PeminjamanID = pg.PeminjamanID
    ORDER BY 
        p.TanggalPeminjaman DESC
    """
    )
    detail_peminjaman = cur.fetchall()

    return render_template(
        "laporan/laporanpeminjaman.html",
        detail_peminjaman=detail_peminjaman,
        now=datetime.now,
    )


# Tambahkan route untuk menambah ulasan
@app.route("/tambah_ulasan/<int:buku_id>", methods=["POST"])
def tambah_ulasan(buku_id):
    if "faiz_UserID" not in session:
        flash("Silakan login terlebih dahulu", "danger")
        return redirect(url_for("login"))

    try:
        # Ambil data dari form
        rating = request.form.get("rating")
        ulasan_text = request.form.get("ulasan")
        user_id = session["faiz_UserID"]

        # Validasi input
        if not rating or not ulasan_text:
            flash("Rating dan ulasan harus diisi", "warning")
            return redirect(url_for("user_ulasanbuku", buku_id=buku_id))

        # Simpan ulasan ke database
        cur = mysql.connection.cursor()
        cur.execute(
            """
            INSERT INTO ulasanbuku 
            (UserID, BukuID, Ulasan, Rating, Tanggal) 
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (user_id, buku_id, ulasan_text, rating),
        )
        mysql.connection.commit()

        # Cek apakah ulasan berhasil disimpan
        if cur.rowcount > 0:
            flash("Ulasan berhasil ditambahkan", "success")
        else:
            flash("Gagal menambahkan ulasan", "danger")

        cur.close()
        return redirect(url_for("user_ulasanbuku", buku_id=buku_id))

    except Exception as e:
        # Tangani error
        flash(f"Terjadi kesalahan: {str(e)}", "danger")
        return redirect(url_for("user_ulasanbuku", buku_id=buku_id))


@app.route("/ncadmin")
def ncadmin():
    return render_template("niceadmin/index.html")


@app.route("/ncadmin/ulasan")
def ncadmin_ulasan():
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM buku")

    buku_data = cur.fetchall()

    cur.close()

    return render_template(
        "niceadmin/ulasan.html",
        buku=buku_data,
        active_page="buku",
    )


@app.route("/ncadmin/ulasanbuku/<int:buku_id>")
def ncadmin_ulasanbuku(buku_id):
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM buku WHERE BukuID = %s", (buku_id,))
    buku_data = cur.fetchone()

    cur.execute(
        """
        SELECT 
            COALESCE(AVG(Rating), 0) as rata_rating, 
            COUNT(*) as jumlah_ulasan
        FROM 
            ulasanbuku
        WHERE 
            BukuID = %s
    """,
        (buku_id,),
    )
    rating_data = cur.fetchone()

    cur.execute(
        """
        SELECT 
            u.*, 
            a.NamaLengkap 
        FROM 
            ulasanbuku u
        JOIN 
            user a ON u.UserID = a.UserID
        WHERE 
            u.BukuID = %s
        ORDER BY u.UlasanID DESC
    """,
        (buku_id,),
    )
    ulasan_data = cur.fetchall()

    cur.close()

    return render_template(
        "niceadmin/ulasanbuku.html",
        ulasan=ulasan_data,
        buku=buku_data,
        rata_rating=rating_data[0],
        jumlah_ulasan=rating_data[1],
        active_page="buku",
    )


UPLOAD_FOLDER = "static/sampulbuku"


# @app.route("/kelola_akun", methods=["GET"])
# def kelola_akun():
#     query = request.args.get("query", "")
#     cur = mysql.connection.cursor()

#     if query:
#         search_query = f"%{query}%"
#         cur.execute(
#             """
#         SELECT * FROM user
#         WHERE Username LIKE %s OR
#               Role LIKE %s OR
#               Email LIKE %s OR
#               NamaLengkap LIKE %s OR
#               Alamat LIKE %s OR
#               Status LIKE %s
#         """,
#             (
#                 search_query,
#                 search_query,
#                 search_query,
#                 search_query,
#                 search_query,
#                 search_query,
#             ),
#         )
#     else:
#         cur.execute("SELECT * FROM user")
#     users_data = cur.fetchall()

#     cur.close()

#     return render_template(
#         "admin/kelola_akun.html", users=users_data, active_page="kelola_akun"
#     )


# @app.route("/kategori_buku")
# def kategori_buku():
#     # Buat koneksi ke database
#     cur = mysql.connection.cursor()

#     cur.execute("SELECT * FROM kategoribuku")

#     kategori_data = cur.fetchall()

#     cur.close()

#     return render_template(
#         "admin/kategori_buku.html", kategori=kategori_data, active_page="kategori_buku"
#     )


@app.route("/dashboard")
def dashboard():
    return render_template("admin/dashboard.html")


@app.route("/laporanbuku")
def admin_laporan_buku():
    faiz_cur = mysql.connection.cursor()

    faiz_cur.execute(
        """
        SELECT 
            b.Judul, 
            b.Penulis, 
            b.Penerbit, 
            b.TahunTerbit,
            b.Stok,
            GROUP_CONCAT(k.NamaKategori SEPARATOR ', ') AS Kategori,
            CASE 
                WHEN p.StatusPeminjaman IN ('Hilang', 'Rusak') THEN p.StatusPeminjaman 
                ELSE '-'
            END AS StatusPeminjaman,
            CASE 
                WHEN AVG(u.Rating) IS NOT NULL THEN AVG(u.Rating) 
                ELSE NULL
            END AS RataRataRating
        FROM 
            buku b
        LEFT JOIN 
            kategoribuku_relasi kr ON b.BukuID = kr.BukuID
        LEFT JOIN 
            kategoribuku k ON kr.KategoriID = k.KategoriID
        LEFT JOIN 
            peminjaman p ON b.BukuID = p.BukuID
        LEFT JOIN 
            ulasanbuku u ON b.BukuID = u.BukuID
        GROUP BY 
            b.BukuID, p.StatusPeminjaman
        """
    )
    laporan_data = faiz_cur.fetchall()

    faiz_cur.close()

    return render_template(
        "laporan/laporanbuku.html",
        laporan_data=laporan_data,
        now=datetime.now,  # Kirim waktu saat ini ke template
    )


@app.route("/logout")
def logout():
    session.clear()

    flash("Anda Telah Berhasil Keluar.", "success")

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
