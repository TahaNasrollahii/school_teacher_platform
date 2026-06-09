# School-Teacher Matching Platform

A Django REST API backend that intelligently connects schools with teachers
based on district proximity, subject compatibility, and salary range overlap.

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Project Structure](#project-structure)
3. [API Reference](#api-reference)
4. [Recommendation Algorithm](#recommendation-algorithm)
5. [Translation / i18n](#translation--i18n)
6. [Running Tests](#running-tests)
7. [Sample Credentials](#sample-credentials)

---

## Quick Start

```bash
# 1. Install dependencies
pip install django djangorestframework django-cors-headers

# 2. Apply migrations
python manage.py migrate

# 3. (Optional) Load sample data
python manage.py shell < seed_data.py

# 4. Compile translations
python manage.py compilemessages

# 5. Start the server
python manage.py runserver
```

---

## Project Structure

```
school_teacher_platform/
├── school_teacher_platform/    ← Django project settings & root URL conf
│   ├── settings.py             ← INSTALLED_APPS, i18n, DRF config
│   └── urls.py
├── schools/                    ← School panel app
│   ├── models.py               ← School, SubjectNeed
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── teachers/                   ← Teacher panel app
│   ├── models.py               ← Teacher, TeachingSubject
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── recommender/                ← Matching engine app
│   ├── models.py               ← TeacherSchoolMatch
│   ├── engine.py               ← Scoring algorithm
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── admin.py
├── locale/
│   └── fa/LC_MESSAGES/
│       ├── django.po           ← Persian (Farsi) translations source
│       └── django.mo           ← Compiled binary (generated)
├── tests/
│   ├── conftest.py             ← Shared pytest fixtures & factories
│   ├── test_models.py          ← Model unit tests
│   ├── test_engine.py          ← Engine unit & integration tests
│   ├── test_schools.py         ← School API tests
│   ├── test_teachers.py        ← Teacher API tests
│   └── test_recommender.py     ← Recommender API tests
├── conftest.py                 ← Root pytest configuration
├── pytest.ini
└── manage.py
```

---

## API Reference

### Authentication

All endpoints except `register` and `login` require a token header:

```
Authorization: Token <your_token_here>
```

---

### School Panel

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/schools/register/` | Create school account + subject needs | Public |
| POST | `/api/schools/login/` | Obtain auth token | Public |
| GET/PUT | `/api/schools/profile/` | Read or update school profile | School |
| GET/POST | `/api/schools/subject-needs/` | List or add subject vacancies | School |
| GET/PUT/DELETE | `/api/schools/subject-needs/<id>/` | Manage a single vacancy | School |
| GET | `/api/schools/list/` | Browse all schools | Authenticated |

#### School Registration Payload

```json
POST /api/schools/register/
{
  "username": "school_sample",
  "password": "securepass123",
  "name": "Sample High School",
  "school_type": "girls",
  "education_level": "high",
  "phone": "02112345678",
  "district": "District 3",
  "address": "10 Pasdaran St, Tehran",
  "subject_needs": [
    {
      "subject_name": "Physics",
      "education_level": "high",
      "min_salary_per_hour": 500000,
      "max_salary_per_hour": 800000
    }
  ]
}
```

**Choices:**

| Field | Values |
|-------|--------|
| `school_type` | `girls` · `boys` · `mixed` |
| `education_level` | `primary` · `middle` · `high` |

---

### Teacher Panel

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/teachers/register/` | Create teacher account + subjects | Public |
| POST | `/api/teachers/login/` | Obtain auth token | Public |
| GET/PUT | `/api/teachers/profile/` | Read or update teacher profile | Teacher |
| GET/POST | `/api/teachers/subjects/` | List or add teaching subjects | Teacher |
| GET/PUT/DELETE | `/api/teachers/subjects/<id>/` | Manage a single subject | Teacher |
| GET | `/api/teachers/list/` | Browse all available teachers | Authenticated |

#### Teacher Registration Payload

```json
POST /api/teachers/register/
{
  "username": "teacher_sample",
  "password": "securepass123",
  "first_name": "Ali",
  "last_name": "Mohammadi",
  "national_id": "1234567890",
  "phone": "09121234567",
  "education_level": "high",
  "district": "District 3",
  "experience_years": 8,
  "schools_history": "Al-Zahra High School, Estedad Institute",
  "publications": "Advanced Physics Textbook\nExam Prep Guide",
  "min_salary_per_hour": 500000,
  "max_salary_per_hour": 900000,
  "bio": "Physics teacher with 8 years experience.",
  "subjects": [
    {
      "subject_name": "Physics",
      "education_level": "high",
      "years_of_experience": 8
    }
  ]
}
```

#### Query Parameters (list endpoints)

```
GET /api/teachers/list/?district=District+3&level=high&subject=Physics
GET /api/schools/list/?district=District+5&level=primary
```

---

### Recommender

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/recommend/school-matches/` | Ranked teacher suggestions for school | School |
| GET | `/api/recommend/teacher-matches/` | Ranked school suggestions for teacher | Teacher |
| PATCH | `/api/recommend/school-match/<id>/status/` | School expresses interest / rejects | School |
| PATCH | `/api/recommend/teacher-match/<id>/status/` | Teacher expresses interest / rejects | Teacher |
| GET | `/api/recommend/stats/` | Aggregate match statistics | Authenticated |
| POST | `/api/recommend/refresh/` | Re-run engine for current user | Authenticated |
| POST | `/api/recommend/run/` | Full engine run (admin only) | Admin |

#### Match Status Workflow

```
              School interested              Teacher interested
pending ──────────────────────────────────────────────────────→ mutual
   │                  school_interested ←──────────────────────────│
   │                  teacher_interested ←──────────────────────────│
   └─────────────────────────────────────────────────────────→ rejected
```

When **both** parties express interest, the status automatically advances to `mutual`.

#### Status Update Payload

```json
PATCH /api/recommend/school-match/5/status/
{
  "status": "school_interested",
  "note": "Please contact us by Friday."
}
```

**Status values:** `pending` · `school_interested` · `teacher_interested` · `mutual` · `rejected`

#### Query Parameters (match endpoints)

```
GET /api/recommend/school-matches/?min_score=50&subject_id=3
GET /api/recommend/teacher-matches/?min_score=40
```

#### Sample Match Response

```json
{
  "id": 1,
  "teacher_name": "Maryam Ahmadi",
  "school_name": "Fatemiyeh Girls School",
  "subject_name": "Physics",
  "match_score": 100.0,
  "salary_overlap_score": 40.0,
  "district_match": true,
  "subject_match": true,
  "level_match": true,
  "status": "school_interested",
  "status_display": "School interested",
  "teacher_salary_range": { "min": 500000, "max": 850000 },
  "school_salary_range":  { "min": 500000, "max": 800000 },
  "school_note": "Please contact us.",
  "teacher_note": ""
}
```

---

## Recommendation Algorithm

Scores are computed per `(teacher, subject_need)` pair.  Only pairs above
`min_score` (default **30**) are stored.

| Component | Max pts | Condition |
|-----------|---------|-----------|
| District match | 35 | `teacher.district == school.district` |
| Salary overlap | 40 | Proportional to range intersection |
| Subject match | 15 | Teacher's subject list contains the required subject |
| Level match | 10 | Primary teaching level matches; 5 pts for partial level match |
| Experience bonus | 5 | 0.5 pt per year, capped at 5 |
| Publications bonus | 3 | 0.5 pt per publication line, capped at 3 |
| **Total** | **≤ 100** | |

### Salary Overlap Formula

```
overlap     = max(0, min(teacher_max, school_max) - max(teacher_min, school_min))
salary_score = (overlap / smaller_range_length) × 40
```

If no overlap exists but the gap is small, **partial credit** (up to 30 % of
the max salary score) is awarded proportional to proximity.

---

## Translation / i18n

The project uses Django's built-in `gettext_lazy` (`_()`) throughout.
All user-facing strings—model verbose names, API messages, validation
errors—are wrapped and appear in the Persian (Farsi) catalogue.

### Workflow

```bash
# 1. Extract new strings from source code
python manage.py makemessages -l fa

# 2. Edit locale/fa/LC_MESSAGES/django.po – fill in msgstr values

# 3. Compile to binary
python manage.py compilemessages
```

### Switching language at runtime

Add the `Accept-Language: fa` header to API requests or set
`LANGUAGE_CODE = 'fa'` in `settings.py` to serve Persian responses globally.

---

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-django

# Run the full suite (130 tests)
python -m pytest tests/ -v

# Run a specific module
python -m pytest tests/test_engine.py -v

# Run with coverage (requires pytest-cov)
pip install pytest-cov
python -m pytest tests/ --cov=. --cov-report=term-missing
```

### Test Layout

| File | Tests | What it covers |
|------|-------|----------------|
| `test_models.py` | 17 | `__str__`, properties, constraints, ordering |
| `test_engine.py` | 28 | Salary overlap, score components, bulk engine, query helpers |
| `test_schools.py` | 28 | Registration, login, profile, CRUD, filtering |
| `test_teachers.py` | 27 | Registration, login, profile, CRUD, filtering |
| `test_recommender.py` | 30 | Match views, status workflow, stats, admin run |
| **Total** | **130** | |

---

## Sample Credentials

| Role | Username | Password |
|------|----------|----------|
| School | `school_tehran1` | `pass1234` |
| School | `school_tehran2` | `pass1234` |
| School | `school_tehran3` | `pass1234` |
| Teacher | `teacher1` (Ali Mohammadi) | `pass1234` |
| Teacher | `teacher2` (Maryam Ahmadi) | `pass1234` |
| Teacher | `teacher3` (Hassan Rezaei) | `pass1234` |
| Teacher | `teacher4` (Zahra Karimi) | `pass1234` |
| Admin | `admin` | `admin1234` |

---

---

# پلتفرم سینک معلم-مدرسه (نسخه فارسی مستندات)

یک بک‌اند REST API مبتنی بر Django برای ارتباط هوشمند معلمان و مدارس
بر اساس منطقه، درس، و همپوشانی بازه حقوقی.

---

## فهرست مطالب
1. [راه‌اندازی سریع](#راه‌اندازی-سریع)
2. [ساختار پروژه](#ساختار-پروژه)
3. [مرجع API](#مرجع-api)
4. [الگوریتم توصیه‌گر](#الگوریتم-توصیه‌گر)
5. [ترجمه و بین‌المللی‌سازی](#ترجمه-و-بین‌المللی‌سازی)
6. [اجرای تست‌ها](#اجرای-تست‌ها)
7. [اطلاعات ورود نمونه](#اطلاعات-ورود-نمونه)

---

## راه‌اندازی سریع

```bash
pip install django djangorestframework django-cors-headers
python manage.py migrate
python manage.py compilemessages
python manage.py runserver
```

---

## ساختار پروژه

```
school_teacher_platform/
├── schools/          ← اپ پنل مدرسه (مدل‌ها، سریالایزرها، ویوها)
├── teachers/         ← اپ پنل معلم
├── recommender/      ← موتور توصیه‌گر و مدیریت تطابق‌ها
├── locale/fa/        ← فایل‌های ترجمه فارسی (.po / .mo)
└── tests/            ← ۱۳۰ تست pytest
```

---

## مرجع API

### احراز هویت

همه endpointها به جز ثبت‌نام و ورود نیاز به هدر دارند:
```
Authorization: Token <توکن>
```

---

### پنل مدرسه

| متد | آدرس | توضیح |
|-----|------|-------|
| POST | `/api/schools/register/` | ثبت‌نام مدرسه + نیازهای درسی |
| POST | `/api/schools/login/` | دریافت توکن |
| GET/PUT | `/api/schools/profile/` | مشاهده/ویرایش پروفایل |
| GET/POST | `/api/schools/subject-needs/` | لیست/اضافه‌کردن نیاز درسی |
| GET/PUT/DELETE | `/api/schools/subject-needs/<id>/` | مدیریت یک نیاز درسی |
| GET | `/api/schools/list/` | لیست مدارس |

#### نمونه payload ثبت‌نام مدرسه

```json
{
  "username": "school_sample",
  "password": "securepass123",
  "name": "دبیرستان نمونه",
  "school_type": "girls",
  "education_level": "high",
  "phone": "02112345678",
  "district": "منطقه ۳",
  "address": "تهران، خیابان پاسداران",
  "subject_needs": [
    {
      "subject_name": "فیزیک",
      "education_level": "high",
      "min_salary_per_hour": 500000,
      "max_salary_per_hour": 800000
    }
  ]
}
```

**مقادیر مجاز:**

| فیلد | مقادیر |
|------|--------|
| `school_type` | `girls` (دخترانه) · `boys` (پسرانه) · `mixed` (مختلط) |
| `education_level` | `primary` (ابتدایی) · `middle` (متوسطه اول) · `high` (متوسطه دوم) |

---

### پنل معلم

| متد | آدرس | توضیح |
|-----|------|-------|
| POST | `/api/teachers/register/` | ثبت‌نام معلم + دروس |
| POST | `/api/teachers/login/` | دریافت توکن |
| GET/PUT | `/api/teachers/profile/` | مشاهده/ویرایش پروفایل |
| GET/POST | `/api/teachers/subjects/` | لیست/اضافه‌کردن درس |
| GET/PUT/DELETE | `/api/teachers/subjects/<id>/` | مدیریت یک درس |
| GET | `/api/teachers/list/` | لیست معلمان |

#### نمونه payload ثبت‌نام معلم

```json
{
  "username": "teacher_sample",
  "password": "securepass123",
  "first_name": "علی",
  "last_name": "محمدی",
  "national_id": "1234567890",
  "phone": "09121234567",
  "education_level": "high",
  "district": "منطقه ۳",
  "experience_years": 8,
  "schools_history": "دبیرستان الزهرا، آموزشگاه استعداد",
  "publications": "کتاب فیزیک پیشرفته\nجزوه کنکور",
  "min_salary_per_hour": 500000,
  "max_salary_per_hour": 900000,
  "subjects": [
    { "subject_name": "فیزیک", "education_level": "high", "years_of_experience": 8 }
  ]
}
```

---

### سیستم توصیه‌گر

| متد | آدرس | توضیح | دسترسی |
|-----|------|-------|---------|
| GET | `/api/recommend/school-matches/` | معلمان پیشنهادی برای مدرسه | مدرسه |
| GET | `/api/recommend/teacher-matches/` | مدارس پیشنهادی برای معلم | معلم |
| PATCH | `/api/recommend/school-match/<id>/status/` | ابراز علاقه/رد توسط مدرسه | مدرسه |
| PATCH | `/api/recommend/teacher-match/<id>/status/` | ابراز علاقه/رد توسط معلم | معلم |
| GET | `/api/recommend/stats/` | آمار تطابق‌ها | هر دو |
| POST | `/api/recommend/refresh/` | بروزرسانی تطابق‌ها | هر دو |
| POST | `/api/recommend/run/` | اجرای کامل موتور | ادمین |

#### وضعیت‌های تطابق

```
pending (در انتظار)
  ↓ مدرسه علاقه‌مند       → school_interested
  ↓ معلم علاقه‌مند         → teacher_interested
  ↓ هر دو علاقه‌مند        → mutual (توافق متقابل) ✅
  ↓ یکی رد کرد            → rejected
```

---

## الگوریتم توصیه‌گر

| معیار | امتیاز | شرط |
|-------|--------|-----|
| هم‌منطقه‌ای | ۳۵ | منطقه معلم = منطقه مدرسه |
| همپوشانی حقوقی | تا ۴۰ | نسبت اشتراک دو بازه |
| تطابق درس | ۱۵ | درس در لیست معلم |
| تطابق مقطع | ۱۰ | مقطع یکسان (۵ برای جزئی) |
| بونوس تجربه | تا ۵ | ۰.۵ به ازای هر سال |
| بونوس تألیفات | تا ۳ | ۰.۵ به ازای هر تألیف |
| **جمع** | **≤ ۱۰۰** | |

### فرمول همپوشانی حقوقی

```
همپوشانی = max(0, min(max_معلم, max_مدرسه) - max(min_معلم, min_مدرسه))
امتیاز = (همپوشانی / کوچک‌ترین بازه) × ۴۰
```

اگر همپوشانی صفر باشد اما فاصله کم، امتیاز جزئی اعطا می‌شود.

---

## ترجمه و بین‌المللی‌سازی

تمام رشته‌های قابل ترجمه با `gettext_lazy` علامت‌گذاری شده‌اند.
فایل ترجمه فارسی در `locale/fa/LC_MESSAGES/django.po` قرار دارد.

```bash
# استخراج رشته‌های جدید
python manage.py makemessages -l fa

# کامپایل
python manage.py compilemessages
```

---

## اجرای تست‌ها

```bash
pip install pytest pytest-django

# اجرای همه تست‌ها (۱۳۰ تست)
python -m pytest tests/ -v

# فقط یک ماژول
python -m pytest tests/test_engine.py -v
```

| فایل | تعداد تست | حوزه |
|------|-----------|------|
| `test_models.py` | ۱۷ | مدل‌ها |
| `test_engine.py` | ۲۸ | موتور امتیازدهی |
| `test_schools.py` | ۲۸ | API مدرسه |
| `test_teachers.py` | ۲۷ | API معلم |
| `test_recommender.py` | ۳۰ | API توصیه‌گر |
| **جمع** | **۱۳۰** | |

---

## اطلاعات ورود نمونه

| نقش | نام کاربری | رمز |
|-----|-----------|-----|
| مدرسه | `school_tehran1` | `pass1234` |
| مدرسه | `school_tehran2` | `pass1234` |
| مدرسه | `school_tehran3` | `pass1234` |
| معلم | `teacher1` (علی محمدی) | `pass1234` |
| معلم | `teacher2` (مریم احمدی) | `pass1234` |
| ادمین | `admin` | `admin1234` |
