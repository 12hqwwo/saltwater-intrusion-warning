"""Kiểm tra hiện trạng cơ sở dữ liệu PostgreSQL: các schema, bảng và số lượng dòng."""
import sys
from pathlib import Path
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from run_webgis import load_local_env
load_local_env()

from backend.database import read_connection

def inspect():
    try:
        with read_connection() as conn:
            db_info = conn.execute("SELECT current_database(), current_user, version()").fetchone()
            print("=" * 60)
            print(f"KẾT NỐI POSTGRESQL THÀNH CÔNG")
            print(f"Database: {db_info['current_database']} | Tài khoản: {db_info['current_user']}")
            print("=" * 60)

            # 1. Kiểm tra Extension PostGIS
            has_postgis = conn.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname='postgis') AS ok").fetchone()['ok']
            print(f"\n1. Extension PostGIS: {'ĐÃ CÀI ĐẶT (OK)' if has_postgis else 'CHƯA CÀI ĐẶT'}")

            # 2. Kiểm tra các Schema
            schemas = conn.execute("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
                ORDER BY schema_name
            """).fetchall()
            schema_names = [s['schema_name'] for s in schemas]
            print(f"\n2. Danh sách Schema hiện có ({len(schema_names)}): {', '.join(schema_names)}")

            # 3. Kiểm tra các bảng trong schema 'public'
            tables_public = conn.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """).fetchall()
            print(f"\n3. Bảng trong schema 'public' ({len(tables_public)} bảng):")
            if not tables_public:
                print("   (Chưa có bảng nào trong schema public)")
            for t in tables_public:
                tname = t['table_name']
                try:
                    cnt = conn.execute(f'SELECT count(*) AS total FROM public."{tname}"').fetchone()['total']
                    print(f"   + public.{tname:<30}: {cnt:>6} dòng")
                except Exception as e:
                    print(f"   + public.{tname:<30}: lỗi ({e})")

            # 4. Kiểm tra schema 'webgis_research' (schema nghiên cứu mới)
            has_research = conn.execute("SELECT to_regclass('webgis_research.snapshot') IS NOT NULL AS ok").fetchone()['ok']
            print(f"\n4. Schema nghiên cứu 'webgis_research':")
            if not has_research:
                print("   -> TRẠNG THÁI: CHƯA NẠP DỮ LIỆU NGHIÊN CỨU VÀO DB.")
                print("   -> Cách đẩy: Chạy lệnh `.venv\\Scripts\\python.exe scripts/import_research_workspace.py --apply`")
            else:
                tables_res = conn.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'webgis_research' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """).fetchall()
                print(f"   -> TRẠNG THÁI: ĐÃ NẠP DỮ LIỆU THÀNH CÔNG ({len(tables_res)} bảng):")
                for t in tables_res:
                    tname = t['table_name']
                    try:
                        cnt = conn.execute(f'SELECT count(*) AS total FROM webgis_research."{tname}"').fetchone()['total']
                        print(f"      + webgis_research.{tname:<25}: {cnt:>6} dòng")
                    except Exception as e:
                        print(f"      + webgis_research.{tname:<25}: lỗi ({e})")
            print("=" * 60)

    except Exception as exc:
        print(f"LỖI KẾT NỐI POSTGRESQL: {exc}")

if __name__ == "__main__":
    inspect()
