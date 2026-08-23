# Task Manager - Django Assignment

A professional, multi-user task manager built with **Django 5.2.17** and **Python 3.11+**, backed by **MySQL**.

## Setup Instructions

This project uses `uv` for lightning-fast dependency management, but standard `pip` works just as well.

### 1. Prerequisites & Environment
Ensure you have the following installed and running before starting:
- **Docker Desktop / Docker Daemon** (must be installed **and currently running**)

*Note: For grading convenience, the `.env` file has been intentionally added to the project in the backend folder. You do not need to configure anything. The entire stack (Django application and MySQL database) is containerized and will spin up together automatically!*

### 2. Run the Entire Application
From the root directory of the repository, simply build and start the Docker containers:
```bash
docker compose up --build
```

**What happens next?**
1. Docker will pull MySQL and spin it up on port `3307`.
2. It will automatically build the Django application image (installing Python 3.11, `uv`, and dependencies).
3. The Django container will patiently wait until the MySQL database is healthy.
4. Once healthy, it will automatically run all database migrations (`python manage.py migrate`).
5. Finally, it will start the Django development server.

You can now navigate to your browser at:
`http://127.0.0.1:8080/`

### 3. Access the App & Create a Superuser


To create an admin superuser account, simply open a new terminal tab and run this inside the running web container:
```bash
docker compose exec web python manage.py createsuperuser
```

---

## ORM & Database Write-Up

### 1. Overdue Tasks Query
**Requirement**: Return tasks where `due_date < today` and `status != Done` in a reusable place.

**ORM Call**: (Located in `tracker/models.py` as a custom Model Manager)
```python
class TaskManager(models.Manager):
    def overdue(self):
        today = timezone.localdate()
        return self.filter(due_date__lt=today).exclude(status='DONE')
```

**Generated SQL**:
```sql
SELECT `tracker_task`.`id`, `tracker_task`.`title`, `tracker_task`.`status`, `tracker_task`.`priority`, `tracker_task`.`due_date`, `tracker_task`.`project_id`, `tracker_task`.`assigned_to_id`, `tracker_task`.`created_at` 
FROM `tracker_task` 
WHERE (`tracker_task`.`due_date` < '2026-08-24' AND NOT (`tracker_task`.`status` = 'DONE'))
```

**Reasoning**: 
By encapsulating this inside a custom `TaskManager`, the logic (`Task.objects.overdue()`) is entirely reusable across any view, celery task, or dashboard without duplicating date resolution. Using `.exclude()` translates natively to a highly efficient `NOT` condition in SQL rather than filtering in Python.

### 2. Per-Project Status Counts
**Requirement**: Return the count of tasks in each status for a given project, without fetching all tasks and counting in Python.

**ORM Call**: (Located in `tracker/views.py` inside `project_list`)
```python
Project.objects.annotate(
    todo_count=Count('tasks', filter=Q(tasks__status='TO DO')),
    in_progress_count=Count('tasks', filter=Q(tasks__status='IN PROGRESS')),
    done_count=Count('tasks', filter=Q(tasks__status='DONE'))
)
```

**Generated SQL**:
```sql
SELECT `tracker_project`.`id`, `tracker_project`.`name`, `tracker_project`.`owner_id`, 
COUNT(CASE WHEN `tracker_task`.`status` = 'TO DO' THEN `tracker_task`.`id` ELSE NULL END) AS `todo_count`, 
COUNT(CASE WHEN `tracker_task`.`status` = 'IN PROGRESS' THEN `tracker_task`.`id` ELSE NULL END) AS `in_progress_count`, 
COUNT(CASE WHEN `tracker_task`.`status` = 'DONE' THEN `tracker_task`.`id` ELSE NULL END) AS `done_count` 
FROM `tracker_project` 
LEFT OUTER JOIN `tracker_task` ON (`tracker_project`.`id` = `tracker_task`.`project_id`) 
GROUP BY `tracker_project`.`id`
```

**Reasoning**: 
Passing `filter=Q(...)` directly into the `Count()` aggregate forces Django to generate standard SQL `CASE WHEN` statements. This computes all three exact status totals across all projects in a single database hit, completely eliminating the massive memory overhead of returning all task rows into Python.

### 3. N+1 Avoidance
**Requirement**: Use `select_related` / `prefetch_related` to avoid querying the DB in a loop.

**ORM Call (Forward FK)**: (Located in `tracker/views.py` inside `dashboard`)
```python
Task.objects.filter(assigned_to=request.user).select_related('project')
```

**Generated SQL**:
```sql
SELECT `tracker_task`.`id`, `tracker_task`.`title`, ..., `tracker_project`.`id`, `tracker_project`.`name` ...
FROM `tracker_task` 
INNER JOIN `tracker_project` ON (`tracker_task`.`project_id` = `tracker_project`.`id`) 
WHERE `tracker_task`.`assigned_to_id` = 1
```

**Reasoning**: 
In the dashboard, we loop over a list of tasks and render `{{ task.project.name }}`. Without `select_related('project')`, Django would execute a separate `SELECT * FROM project WHERE id = ?` for every single task row rendered. By using `select_related`, we perform a SQL `INNER JOIN`, gathering all tasks and their respective projects simultaneously in precisely one query.

### 4. Database Indexing
**Requirement**: Add exactly one justified database index.

**Code**: (Located in `tracker/models.py` inside the `Task` model)
```python
class Meta:
    indexes = [
        models.Index(fields=['status', 'due_date'], name='idx_status_due_date'),
    ]
```

**Justification**:
The application features a heavily utilized "Overdue Tasks" query on the dashboard which filters heavily by both `due_date` and `status` concurrently (`WHERE due_date < today AND status != 'DONE'`). I chose to add a composite index on exactly `(status, due_date)`. This composite index perfectly covers the `WHERE` clause of this critical query, allowing the database engine to quickly seek the exact subset of overdue rows directly from the B-tree rather than performing an expensive, full table scan on the `tracker_task` table as the dataset grows.
