from app.repositories.task import TaskRepository
from app.services.task import TaskService

task_repository = TaskRepository()


def get_task_service() -> TaskService:
    return TaskService(repository=task_repository)
