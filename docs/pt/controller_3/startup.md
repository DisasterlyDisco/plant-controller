
# Enable automatic start-up of systemd user instances
```bash
loginctl enable-linger
```

# Import path into systemd user instances
Add `systemctl --user import-environment PATH` to `~/.bashrc`