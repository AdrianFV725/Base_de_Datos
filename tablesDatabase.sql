-- Esquema para PostgreSQL basado en el diagrama proporcionado

-- Tabla persona_info
CREATE TABLE IF NOT EXISTS person_info (
    id_person         SERIAL          PRIMARY KEY,
    first_name        VARCHAR(100),
    first_surname     VARCHAR(100)
);

-- Tabla sexes
CREATE TABLE IF NOT EXISTS sexes (
    id_sex            SERIAL          PRIMARY KEY,
    sex               VARCHAR(50)     NOT NULL
);

-- Tabla marital_statuses
CREATE TABLE IF NOT EXISTS marital_statuses (
    id_marital        SERIAL          PRIMARY KEY,
    status            VARCHAR(50)     NOT NULL
);

-- Tabla education_levels
CREATE TABLE IF NOT EXISTS education_levels (
    id_education      SERIAL          PRIMARY KEY,
    level             VARCHAR(100)    NOT NULL
);

-- Tabla legal_statuses
CREATE TABLE IF NOT EXISTS legal_statuses (
    id_legal          SERIAL          PRIMARY KEY,
    status            VARCHAR(100)    NOT NULL
);

-- Tabla countries
CREATE TABLE IF NOT EXISTS countries (
    id_country        SERIAL          PRIMARY KEY,
    country           VARCHAR(100)    NOT NULL
);

-- Tabla regions
CREATE TABLE IF NOT EXISTS regions (
    id_region         SERIAL          PRIMARY KEY,
    region_name       VARCHAR(100)    NOT NULL,
    id_country        INTEGER         REFERENCES countries(id_country)
);

-- Tabla travel_methods
CREATE TABLE IF NOT EXISTS travel_methods (
    id_travel_method  SERIAL          PRIMARY KEY,
    method            VARCHAR(100)    NOT NULL
);

-- Tabla demographic_info
CREATE TABLE IF NOT EXISTS demographic_info (
    id_demography     SERIAL          PRIMARY KEY,
    id_main_person    INTEGER         REFERENCES person_info(id_person),
    id_sex            INTEGER         REFERENCES sexes(id_sex),
    id_marital        INTEGER         REFERENCES marital_statuses(id_marital),
    id_education      INTEGER         REFERENCES education_levels(id_education),
    id_occupation     INTEGER,
    id_religion       INTEGER,
    id_legal          INTEGER         REFERENCES legal_statuses(id_legal)
);

-- Tabla travel_info
CREATE TABLE IF NOT EXISTS travel_info (
    id_travel         SERIAL          PRIMARY KEY,
    departure_date    DATE,
    departure_country INTEGER         REFERENCES countries(id_country),
    departure_region  INTEGER         REFERENCES regions(id_region),
    motive_migration  VARCHAR(200),
    id_travel_method  INTEGER         REFERENCES travel_methods(id_travel_method),
    travel_duration   DATE,
    return_plans      VARCHAR(200)
);

-- Tabla text_files
CREATE TABLE IF NOT EXISTS text_files (
    id_text           SERIAL          PRIMARY KEY,
    path              VARCHAR(255)    NOT NULL,
    story_summary     TEXT,
    id_demography     INTEGER         REFERENCES demographic_info(id_demography),
    id_travel         INTEGER         REFERENCES travel_info(id_travel)
);

-- Tabla image_files
CREATE TABLE IF NOT EXISTS image_files (
    id_img            SERIAL          PRIMARY KEY,
    path              VARCHAR(255)    NOT NULL
);

-- Tabla text_image_link (relación muchos a muchos entre textos e imágenes)
CREATE TABLE IF NOT EXISTS text_image_link (
    id_text           INTEGER         NOT NULL,
    id_img            INTEGER         NOT NULL,
    PRIMARY KEY (id_text, id_img),
    FOREIGN KEY (id_text) REFERENCES text_files(id_text),
    FOREIGN KEY (id_img) REFERENCES image_files(id_img)
);

-- Tabla keywords
CREATE TABLE IF NOT EXISTS keywords (
    id_keyword        SERIAL          PRIMARY KEY,
    keyword           VARCHAR(100)    NOT NULL,
    id_text           INTEGER         REFERENCES text_files(id_text)
);

-- Tabla family_link
CREATE TABLE IF NOT EXISTS family_link (
    id_demography     INTEGER         NOT NULL,
    id_person         INTEGER         NOT NULL,
    PRIMARY KEY (id_demography, id_person),
    FOREIGN KEY (id_demography) REFERENCES demographic_info(id_demography),
    FOREIGN KEY (id_person) REFERENCES person_info(id_person)
);

-- Tabla admins
CREATE TABLE IF NOT EXISTS admins (
    id_admin          SERIAL          PRIMARY KEY,
    email             VARCHAR(100)    NOT NULL,
    password          VARCHAR(255)    NOT NULL
);

-- Tabla passwords_resets
CREATE TABLE IF NOT EXISTS passwords_resets (
    id_reset          SERIAL          PRIMARY KEY,
    id_admin          INTEGER         REFERENCES admins(id_admin),
    reset_token       VARCHAR(255)    NOT NULL UNIQUE,
    requested_at      VARCHAR(50)     NOT NULL,
    expires_at        TIMESTAMP       NOT NULL,
    used_at           TIMESTAMP
);

-- Índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_demographic_main_person ON demographic_info(id_main_person);
CREATE INDEX IF NOT EXISTS idx_text_files_demography ON text_files(id_demography);
CREATE INDEX IF NOT EXISTS idx_text_files_travel ON text_files(id_travel);
CREATE INDEX IF NOT EXISTS idx_keywords_text ON keywords(id_text);
CREATE INDEX IF NOT EXISTS idx_family_link_person ON family_link(id_person);
CREATE INDEX IF NOT EXISTS idx_family_link_demography ON family_link(id_demography);
CREATE INDEX IF NOT EXISTS idx_travel_method ON travel_info(id_travel_method);
CREATE INDEX IF NOT EXISTS idx_travel_country ON travel_info(departure_country);
CREATE INDEX IF NOT EXISTS idx_travel_region ON travel_info(departure_region);
CREATE INDEX IF NOT EXISTS idx_region_country ON regions(id_country);