from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

app = Flask(__name__)


def check_and_create_database():
    try:
        engine = create_engine("mysql://root:@localhost/", future=True)

        with engine.connect() as connection:
            result = connection.execute(text("SHOW DATABASES LIKE 'FAIZ_UKKPerpus'"))
            database_exists = result.fetchone() is not None

            if not database_exists:
                connection.execute(text("CREATE DATABASE FAIZ_UKKPerpus"))
                connection.commit()
                print("Database 'FAIZ_UKKPerpus' berhasil dibuat.")
            else:
                print("Database 'FAIZ_UKKPerpus' sudah ada.")

        app.config["SQLALCHEMY_DATABASE_URI"] = (
            "mysql+pymysql://root:@localhost/FAIZ_UKKPerpus"
        )
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        db = SQLAlchemy(app)

        class User(db.Model):
            __tablename__ = "user"
            UserID = db.Column(db.Integer, primary_key=True)
            Username = db.Column(db.String(255), nullable=False)
            Password = db.Column(db.String(255), nullable=False)
            Role = db.Column(db.String(10), nullable=False)
            Email = db.Column(db.String(255), nullable=False)
            NamaLengkap = db.Column(db.String(255))
            Alamat = db.Column(db.Text)
            Status = db.Column(db.String(20))

        class Buku(db.Model):
            __tablename__ = "buku"
            BukuID = db.Column(db.Integer, primary_key=True)
            Judul = db.Column(db.String(255))
            Penulis = db.Column(db.String(255))
            Penerbit = db.Column(db.String(255))
            TahunTerbit = db.Column(db.Integer)
            Stok = db.Column(db.Integer)
            Gambar = db.Column(db.String(255))

        class KategoriBuku(db.Model):
            __tablename__ = "kategoribuku"
            KategoriID = db.Column(db.Integer, primary_key=True)
            NamaKategori = db.Column(db.String(255))

        class KategoriBukuRelasi(db.Model):
            __tablename__ = "kategoribuku_relasi"
            KategoriBukuID = db.Column(db.Integer, primary_key=True)
            BukuID = db.Column(db.Integer, db.ForeignKey("buku.BukuID"), nullable=False)
            KategoriID = db.Column(
                db.Integer, db.ForeignKey("kategoribuku.KategoriID"), nullable=False
            )

        class Peminjaman(db.Model):
            __tablename__ = "peminjaman"
            PeminjamanID = db.Column(db.Integer, primary_key=True)
            UserID = db.Column(db.Integer, db.ForeignKey("user.UserID"), nullable=False)
            BukuID = db.Column(db.Integer, db.ForeignKey("buku.BukuID"), nullable=False)
            TanggalPeminjaman = db.Column(db.Date)
            TanggalPengembalian = db.Column(db.Date)
            StatusPeminjaman = db.Column(db.String(50))

        class Pengembalian(db.Model):
            __tablename__ = "pengembalian"
            PengembalianID = db.Column(db.Integer, primary_key=True)
            PeminjamanID = db.Column(
                db.Integer, db.ForeignKey("peminjaman.PeminjamanID"), nullable=False
            )
            TanggalDikembalikan = db.Column(db.Date)
            Denda = db.Column(db.String(255))
            NilaiDenda = db.Column(db.Integer)

        class UlasanBuku(db.Model):
            __tablename__ = "ulasanbuku"
            UlasanID = db.Column(db.Integer, primary_key=True)
            UserID = db.Column(db.Integer, db.ForeignKey("user.UserID"), nullable=False)
            BukuID = db.Column(db.Integer, db.ForeignKey("buku.BukuID"), nullable=False)
            Ulasan = db.Column(db.Text)
            Rating = db.Column(db.Integer)
            Tanggal = db.Column(db.DateTime)

        class KoleksiPribadi(db.Model):
            __tablename__ = "koleksipribadi"
            KoleksiID = db.Column(db.Integer, primary_key=True)
            UserID = db.Column(db.Integer, db.ForeignKey("user.UserID"), nullable=False)
            BukuID = db.Column(db.Integer, db.ForeignKey("buku.BukuID"), nullable=False)

        class LogAktivitas(db.Model):
            __tablename__ = "logaktivitas"

            LogID = db.Column(db.Integer, primary_key=True, autoincrement=True)
            UserID = db.Column(db.Integer, db.ForeignKey("user.UserID"), nullable=False)
            Aksi = db.Column(db.String(255), nullable=False)
            Tanggal = db.Column(db.TIMESTAMP, nullable=False)

        # class KategoriDenda(db.Model):
        #     __tablename__ = "kategoridenda"
        #     KategoriDendaID = db.Column(db.Integer, primary_key=True)
        #     NamaDenda = db.Column(db.String(255))
        #     NilaiDenda = db.Column(db.Integer)

        # class DendaPeminjaman(db.Model):
        #     __tablename__ = "dendapeminjaman"
        #     DendaID = db.Column(db.Integer, primary_key=True)
        #     PeminjamanID = db.Column(
        #         db.Integer, db.ForeignKey("peminjaman.PeminjamanID"), nullable=False
        #     )
        #     KategoriDendaID = db.Column(
        #         db.Integer,
        #         db.ForeignKey("kategoridenda.KategoriDendaID"),
        #         nullable=False,
        #     )
        #     TanggalDenda = db.Column(db.Date)
        #     NilaiDenda = db.Column(db.Integer)

        with app.app_context():
            db.create_all()
            print("Tabel-tabel berhasil dibuat/diperbarui.")

        return db

    except OperationalError as e:
        print(f"Error koneksi database: {e}")
        return None


database = check_and_create_database()

if __name__ == "__main__":
    if database is not None:
        app.run(debug=True)
    else:
        print("Gagal terhubung ke database.")
