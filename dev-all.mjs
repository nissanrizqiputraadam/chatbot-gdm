import { spawn, spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));
const isWindows = process.platform === "win32";
const children = [];
let stopping = false;

function detectPython() {
  if (process.env.PYTHON) return process.env.PYTHON;
  const candidates = isWindows ? ["py", "python", "python3"] : ["python3", "python"];
  for (const cmd of candidates) {
    try {
      const res = spawnSync(cmd, ["--version"], { stdio: "ignore" });
      if (res.status === 0) return cmd;
    } catch {}
  }
  return isWindows ? "python" : "python3";
}

function stop(exitCode = 0) {
  if (stopping) return;
  stopping = true;

  for (const { child } of children) {
    if (!child.pid || child.exitCode !== null) continue;
    if (isWindows) {
      spawn("taskkill", ["/pid", String(child.pid), "/T", "/F"], { stdio: "ignore" });
    } else {
      child.kill("SIGTERM");
    }
  }
  setTimeout(() => process.exit(exitCode), 300);
}

function start(label, command, args, cwd) {
  const child = spawn(command, args, { cwd, stdio: "inherit" });
  children.push({ child });
  child.on("error", (error) => {
    console.error(`[${label}] Gagal dijalankan: ${error.message}`);
    stop(1);
  });
  child.on("exit", (code) => {
    if (!stopping) {
      console.log(`[${label}] berhenti dengan kode ${code ?? "unknown"}.`);
      stop(code || 0);
    }
  });
}

process.on("SIGINT", () => stop(0));
process.on("SIGTERM", () => stop(0));

const pythonCmd = detectPython();
console.log(`[dev:all] Menggunakan Python: ${pythonCmd}`);
console.log("Menjalankan backend dan frontend. Tekan Ctrl+C untuk menghentikan keduanya.");

start("backend", pythonCmd, ["-m", "uvicorn", "main:app", "--reload", "--app-dir", "backend"], root);

if (isWindows) {
  start("frontend", "cmd.exe", ["/d", "/s", "/c", "npm run dev"], path.join(root, "frontend"));
} else {
  start("frontend", "npm", ["run", "dev"], path.join(root, "frontend"));
}
