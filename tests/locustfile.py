import os
from locust import HttpUser, task, between


class ApiUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        token = os.getenv("LOCUST_TOKEN")
        if token:
            self.client.headers.update({"Authorization": f"Bearer {token}"})
            return

        username = os.getenv("LOCUST_USERNAME", "admin")
        password = os.getenv("LOCUST_PASSWORD", "admin123")
        response = self.client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
            name="/api/v1/auth/login",
        )
        if response.status_code == 200:
            data = response.json().get("data", {})
            token = data.get("token")
            if token:
                self.client.headers.update({"Authorization": f"Bearer {token}"})

        self.scope = os.getenv("LOCUST_SCOPE", "all")
        self.task_id = os.getenv("LOCUST_TASK_ID")

    @task(5)
    def list_tasks(self):
        self.client.get("/api/v1/tasks", params={"scope": self.scope}, name="/api/v1/tasks")

    @task(3)
    def unread_notifications(self):
        self.client.get("/api/v1/notifications/unread-count", name="/api/v1/notifications/unread-count")

    @task(2)
    def ai_effect_report(self):
        self.client.get("/api/v1/reports/ai-effect", name="/api/v1/reports/ai-effect")

    @task(2)
    def profile(self):
        self.client.get("/api/v1/profile", name="/api/v1/profile")

    @task(1)
    def task_detail(self):
        if not self.task_id:
            return
        self.client.get(f"/api/v1/tasks/{self.task_id}", name="/api/v1/tasks/{id}")

    @task(1)
    def task_ai_progress(self):
        if not self.task_id:
            return
        self.client.get(f"/api/v1/tasks/{self.task_id}/ai-progress", name="/api/v1/tasks/{id}/ai-progress")
