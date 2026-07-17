from app.jobs import JobManager

def test_job_lifecycle():
    manager = JobManager()
    job = manager.create("abc", "demo")
    assert job.status == "queued"
    manager.update(job.id, status="running", progress=45)
    assert manager.get(job.id).progress == 45
    manager.update(job.id, status="complete", progress=100)
    assert manager.get(job.id).status == "complete"
