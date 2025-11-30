import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 1. Intentamos leer la URL de la base de datos de la Nube (Render)
# Si no existe (porque estás en tu PC), usamos la local "torneo.db"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

if not SQLALCHEMY_DATABASE_URL:
    # Modo Local (Tu PC)
    SQLALCHEMY_DATABASE_URL = "sqlite:///./torneo.db"
    connect_args = {"check_same_thread": False} # Necesario solo para SQLite
else:
    # Modo Nube (PostgreSQL)
    # Corrección pequeña: Render a veces da la URL con "postgres://", pero Python necesita "postgresql://"
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
    connect_args = {}

# 2. Creamos el Motor
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)

# 3. Creamos la Sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. La Base para los modelos
Base = declarative_base()