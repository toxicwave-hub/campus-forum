# 论坛后台管理说明

## 角色

- 站长：使用 Django 超级管理员账号，拥有全部权限。只保留少量可信账号。
- 论坛管理员：管理板块、帖子、回帖、举报、附件和版主任命，不管理账号密码，不查看私信。
- 论坛版主：处理帖子、回帖、举报和违规附件，不修改板块，不管理账号密码，不查看私信。

## 初始化角色

```bash
python manage.py setup_forum_roles
```

授权论坛管理员：

```bash
python manage.py setup_forum_roles --administrator 用户名
```

授权论坛版主：

```bash
python manage.py setup_forum_roles --moderator 用户名
```

## 日常管理建议

1. 优先处理举报，再处理明显违规内容。
2. 删除内容前先确认原因，避免误删。
3. 不要共用站长账号，不要把站长密码发送给别人。
4. 私信只在确有安全或合规需要时由站长核查。
5. 定期备份 SQLite 数据库和用户上传文件。
