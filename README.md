# Професійний Python — лабораторні роботи 1–10

Лис Артур, ФЕП-31с, варіант 1 («Система обліку студентів»).

Кожен каталог `Lab_NN` містить стан наскрізного проєкту `student-manager` на момент завершення відповідної
лабораторної роботи (код, тести, README) та звіт `Lab_NN_Lys.docx` / `.pdf`.
Повна історія проєкту з Git-комітами та CI: https://github.com/ArturLys/student-manager

| Каталог | Тема | Звіт |
|---------|------|------|
| [Lab_01](Lab_01/) | Основи Python, модель Student, реєстр, CLI | [docx](Lab_01/Lab_01_Lys.docx) · [pdf](Lab_01/Lab_01_report.pdf) |
| [Lab_02](Lab_02/) | Функції, замикання, декоратори, аналітика | [docx](Lab_02/Lab_02_Lys.docx) · [pdf](Lab_02/Lab_02_report.pdf) |
| [Lab_03](Lab_03/) | Ітератори, генератори, потокова обробка | [docx](Lab_03/Lab_03_Lys.docx) · [pdf](Lab_03/Lab_03_report.pdf) |
| [Lab_04](Lab_04/) | ООП, типізація, доменна модель | [docx](Lab_04/Lab_04_Lys.docx) · [pdf](Lab_04/Lab_04_report.pdf) |
| [Lab_05](Lab_05/) | Файли, винятки, конфігурація, логування | [docx](Lab_05/Lab_05_Lys.docx) · [pdf](Lab_05/Lab_05_report.pdf) |
| [Lab_06](Lab_06/) | Автоматизоване тестування (pytest, mocks, coverage) | [docx](Lab_06/Lab_06_Lys.docx) · [pdf](Lab_06/Lab_06_report.pdf) |
| [Lab_07](Lab_07/) | Бази даних: SQLite, SQLAlchemy, Alembic | [docx](Lab_07/Lab_07_Lys.docx) · [pdf](Lab_07/Lab_07_report.pdf) |
| [Lab_08](Lab_08/) | REST API: FastAPI, asyncio, HTTPX | [docx](Lab_08/Lab_08_Lys.docx) · [pdf](Lab_08/Lab_08_report.pdf) |
| [Lab_09](Lab_09/) | Паралельність, профілювання, оптимізація | [docx](Lab_09/Lab_09_Lys.docx) · [pdf](Lab_09/Lab_09_report.pdf) |
| [Lab_10](Lab_10/) | Production: пакет, Docker, CI/CD | [docx](Lab_10/Lab_10_Lys.docx) · [pdf](Lab_10/Lab_10_report.pdf) |

Запуск будь-якої лабораторної: `cd Lab_NN && python -m venv .venv && .venv/Scripts/pip install -e ".[test]" && pytest`
(для ЛР7–10 додатково `".[db]"`, `".[api]"`, `".[perf]"`).
