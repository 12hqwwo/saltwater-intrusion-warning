import xarray as xr
import sys

def inspect_nc(file_path):
    print(f"--- Đọc thông tin tệp NetCDF: {file_path} ---")
    try:
        ds = xr.open_dataset(file_path)
        print("\n1. CHIỀU DỮ LIỆU (Dimensions):")
        for dim, size in ds.sizes.items():
            print(f"   - {dim}: {size}")
            
        print("\n2. CÁC BIẾN (Variables):")
        for var in ds.data_vars:
            print(f"   - {var}: shape={ds[var].shape}, dtype={ds[var].dtype}")
            if 'long_name' in ds[var].attrs:
                print(f"     + Mô tả (long_name): {ds[var].attrs['long_name']}")
            if 'units' in ds[var].attrs:
                print(f"     + Đơn vị (units): {ds[var].attrs['units']}")
                
        print("\n3. THUỘC TÍNH CHUNG (Global Attributes):")
        for attr, val in ds.attrs.items():
            print(f"   - {attr}: {val}")
            
        ds.close()
    except Exception as e:
        print(f" Lỗi khi đọc file: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        nc_file = sys.argv[1]
    else:
        import glob
        files = glob.glob(r"data/raw/waterlevel/glofas_tanchau/*.nc")
        if files:
            nc_file = files[0]
            print(f"Không truyền tên file, tự động chọn file đầu tiên tìm thấy: {nc_file}")
        else:
            print("Không tìm thấy file .nc nào trong thư mục data/raw/waterlevel/glofas_tanchau/")
            sys.exit(1)
            
    inspect_nc(nc_file)
