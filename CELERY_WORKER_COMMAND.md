Celery worker başlatmak için:

```bash
cd /Users/oguzhanbozkurt/Code/mevzuatgpt-server
python -m celery -A tasks.celery_app worker --loglevel=info --concurrency=1
```

Yargıtay için ayrı worker (yalnızca `yargitay` queue):

```bash
cd /Users/oguzhanbozkurt/Code/mevzuatgpt-server
python -m celery -A tasks.celery_app worker --loglevel=info --concurrency=1 -Q yargitay
```
