# Project Health Check Script

import os
import sys
from pathlib import Path

def check_python():
    """Check Python version and dependencies"""
    print("=" * 60)
    print("PYTHON ENVIRONMENT CHECK")
    print("=" * 60)
    
    version = sys.version_info
    print(f"✓ Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("✗ ERROR: Python 3.9+ required")
        return False
    
    # Check key packages
    packages = [
        'fastapi', 'uvicorn', 'sqlalchemy', 'pydantic', 'chromadb',
        'sentence_transformers', 'rank_bm25', 'flashrank', 'pyotp',
        'passlib', 'python_jose', 'cryptography'
    ]
    
    missing = []
    for pkg in packages:
        try:
            __import__(pkg.replace('-', '_'))
            print(f"✓ {pkg}")
        except ImportError:
            print(f"✗ {pkg} - MISSING")
            missing.append(pkg)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    print("✓ All packages installed\n")
    return True

def check_database():
    """Check database setup"""
    print("=" * 60)
    print("DATABASE CHECK")
    print("=" * 60)
    
    db_path = Path("Backend/cybersecurity.db")
    if db_path.exists():
        size = db_path.stat().st_size
        print(f"✓ Database exists: {size:,} bytes")
    else:
        print("✗ Database not found")
        print("  Run: python Backend/init_db.py")
        return False
    
    chroma_path = Path("Backend/chroma_db")
    if chroma_path.exists():
        print(f"✓ ChromaDB directory exists")
    else:
        print("✗ ChromaDB not found")
        return False
    
    print()
    return True

def check_environment():
    """Check environment variables"""
    print("=" * 60)
    print("ENVIRONMENT VARIABLES")
    print("=" * 60)
    
    env_file = Path("Backend/.env")
    if env_file.exists():
        print(f"✓ .env file found")
    else:
        print("✗ .env file not found (using defaults)")
    
    from dotenv import load_dotenv
    load_dotenv("Backend/.env")
    
    vars_to_check = {
        'SECRET_KEY': 'JWT Secret Key',
        'REFRESH_SECRET_KEY': 'JWT Refresh Secret',
        'API_URL': 'Backend API URL',
        'FRONTEND_URL': 'Frontend URL'
    }
    
    for var, desc in vars_to_check.items():
        val = os.getenv(var)
        if val:
            print(f"✓ {var}: {val[:20]}...")
        else:
            print(f"⚠️  {var}: (using default)")
    
    print()
    return True

def check_ports():
    """Check if required ports are available"""
    print("=" * 60)
    print("PORT AVAILABILITY CHECK")
    print("=" * 60)
    
    import socket
    
    ports = {
        8000: 'Backend (FastAPI)',
        4200: 'Frontend (Angular)'
    }
    
    available = True
    for port, service in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            print(f"✗ Port {port} ({service}): IN USE")
            available = False
        else:
            print(f"✓ Port {port} ({service}): Available")
    
    print()
    return available

def check_files():
    """Check all required files exist"""
    print("=" * 60)
    print("FILE STRUCTURE CHECK")
    print("=" * 60)
    
    required_files = [
        'Backend/main.py',
        'Backend/database.py',
        'Backend/auth_utils.py',
        'Backend/init_db.py',
        'Frontend/package.json',
        'Frontend/src/main.ts',
        'Frontend/src/app/app.routes.ts',
        'requirements.txt'
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} - MISSING")
            all_exist = False
    
    print()
    return all_exist

def main():
    """Run all checks"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  CYBERBOT PROJECT - HEALTH CHECK SCRIPT  ".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    checks = [
        ("Python & Dependencies", check_python),
        ("Database Setup", check_database),
        ("Environment Configuration", check_environment),
        ("Port Availability", check_ports),
        ("File Structure", check_files)
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"✗ {name}: {str(e)}\n")
            results[name] = False
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print()
    
    if all(results.values()):
        print("✓ All checks passed! Your project is ready to start.")
        print()
        print("To start the project:")
        print("  1. Terminal 1: START_BACKEND.bat")
        print("  2. Terminal 2: START_FRONTEND.bat")
        print("  3. Open: http://127.0.0.1:4200")
        return 0
    else:
        print("✗ Some checks failed. See details above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
