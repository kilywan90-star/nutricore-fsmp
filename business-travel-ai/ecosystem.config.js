module.exports = {
  apps: [
    {
      name: "business-travel-ai",
      script: "npm",
      args: "start",
      cwd: "/opt/business-travel-ai",
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: "512M",
      env: {
        NODE_ENV: "production",
        PORT: 3000,
      },
    },
  ],
};
