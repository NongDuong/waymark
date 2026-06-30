# Backup & Restore Database (Cloudflare R2)

## Backup thủ công

```bash
~/waymark/scripts/backup_r2.sh
```

File được upload lên R2 tại: `s3://waymark-media/backups/waymark_YYYYMMDD_HHMMSS.sql.gz`

---

## Cron backup tự động (3h sáng mỗi ngày)

```bash
(crontab -l 2>/dev/null; echo "0 3 * * * /root/waymark/scripts/backup_r2.sh >> /root/backup.log 2>&1") | crontab -
```

Kiểm tra cron:
```bash
crontab -l
```

Xem log backup:
```bash
tail -f /root/backup.log
```

---

## Chuyển sang server mới

### Bước 1 — Cài đặt server mới

```bash
apt install -y docker.io docker-compose-plugin awscli git
```

### Bước 2 — Clone repo và cấu hình

```bash
git clone https://github.com/NongDuong/waymark.git /root/waymark
cd /root/waymark
```

> **Quan trọng:** Copy file `.env` sang server mới (không có trên GitHub).
> File `.env` chứa: database credentials, R2 credentials, JWT secret, Firebase credentials...

### Bước 3 — Khởi động app

```bash
docker compose up -d
```

Kiểm tra containers đã chạy:
```bash
docker compose ps
```

### Bước 4 — Restore data từ R2

```bash
chmod +x ~/waymark/scripts/restore_r2.sh
~/waymark/scripts/restore_r2.sh
```

Script sẽ hiển thị danh sách backup có sẵn (20 file mới nhất), nhập tên file muốn restore.

### Bước 5 — Thiết lập lại cron backup

```bash
(crontab -l 2>/dev/null; echo "0 3 * * * /root/waymark/scripts/backup_r2.sh >> /root/backup.log 2>&1") | crontab -
```

---

## Restore thủ công từ file cụ thể

```bash
# Xem danh sách backup trên R2
source ~/waymark/.env
AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID}" \
AWS_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY}" \
aws s3 ls s3://waymark-media/backups/ \
    --endpoint-url "https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com" \
    --region auto | sort -r

# Restore
~/waymark/scripts/restore_r2.sh
```

---

## Lưu ý quan trọng

| Lệnh | Mức độ | Ghi chú |
|------|--------|---------|
| `docker compose restart web` | ✅ An toàn | Dùng khi deploy code mới |
| `git pull && docker compose restart web` | ✅ An toàn | Lệnh deploy chuẩn |
| `docker compose down` | ✅ An toàn | Dừng app, data giữ nguyên |
| `docker compose down -v` | ☠️ Nguy hiểm | **XÓA TOÀN BỘ DATA** |
| `docker volume prune` | ☠️ Nguy hiểm | **XÓA TOÀN BỘ DATA** |
