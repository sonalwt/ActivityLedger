"""
Migration: Backfill noise project names (Data, Dia, IDE Work, src, app, etc.)
Run once on the server: python migrate_noise_projects.py

Steps:
  1. Fix browser/Dia activities — extract GitHub repo name from window titles
  2. Fix IDE activities (Cursor, Code) — assign project from concurrent browser activity
"""

import re
from datetime import timedelta
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:asdf1234@localhost:5432/timesheet")
engine = create_engine(DATABASE_URL)

NOISE_PROJECTS = {'data', 'dia', 'ide work', 'src', 'app', 'temp', 'tmp',
                  'backend', 'frontend', 'server', 'client', 'lib', 'dist',
                  'build', 'test', 'tests', 'scripts', 'docs', 'output',
                  'input', 'logs', 'cache', 'general', 'unknown', ''}

# Matches "CapOrg/repo-name" in window titles (e.g. Mahindra-Manulife/mahindra-manulife-retail)
GITHUB_REPO_RE = re.compile(r'[A-Z][A-Za-z0-9-]*/([A-Za-z][A-Za-z0-9-]+)')


def extract_github_repo(window_title: str):
    m = GITHUB_REPO_RE.search(window_title or '')
    if m and len(m.group(1)) > 3:
        return m.group(1)
    return None


def is_noise(project_name: str) -> bool:
    return (project_name or '').strip().lower() in NOISE_PROJECTS


def run_migration():
    with engine.begin() as conn:

        # ----------------------------------------------------------------
        # STEP 1: Fix browser/Dia activities that have GitHub PR titles
        # ----------------------------------------------------------------
        print("Step 1: Fixing browser/Dia activities with GitHub titles...")

        browser_rows = conn.execute(text("""
            SELECT id, window_title, project_name, developer_id
            FROM activity_records
            WHERE LOWER(application_name) IN ('dia', 'chrome', 'firefox', 'edge', 'safari', 'brave')
              AND (project_name IS NULL OR LOWER(project_name) = ANY(:noise))
            ORDER BY timestamp
        """), {"noise": list(NOISE_PROJECTS)}).fetchall()

        browser_fixed = 0
        for row in browser_rows:
            repo = extract_github_repo(row[1])
            if repo:
                conn.execute(text("""
                    UPDATE activity_records
                    SET project_name = :repo, project_type = 'Development', category = 'browser'
                    WHERE id = :id
                """), {"repo": repo, "id": row[0]})
                browser_fixed += 1

        print(f"  Fixed {browser_fixed} browser/Dia records with GitHub repo names.")

        # ----------------------------------------------------------------
        # STEP 2: Fix IDE activities (Cursor, Code, etc.) with noise names
        #         → look at concurrent browser activity within ±30 min
        # ----------------------------------------------------------------
        print("Step 2: Fixing IDE activities using concurrent browser context...")

        ide_rows = conn.execute(text("""
            SELECT id, developer_id, timestamp, window_title, project_name
            FROM activity_records
            WHERE LOWER(application_name) IN ('cursor', 'code', 'visual studio code',
                                               'pycharm', 'intellij', 'xcode')
              AND (project_name IS NULL OR LOWER(project_name) = ANY(:noise))
            ORDER BY developer_id, timestamp
        """), {"noise": list(NOISE_PROJECTS)}).fetchall()

        ide_fixed = 0
        for row in ide_rows:
            rec_id, dev_id, ts, wt, pn = row

            # Find the most recent browser activity with a real project name within 30 min
            browser_proj = conn.execute(text("""
                SELECT project_name
                FROM activity_records
                WHERE developer_id = :dev_id
                  AND category = 'browser'
                  AND project_name IS NOT NULL
                  AND LOWER(project_name) != ALL(:noise)
                  AND timestamp BETWEEN :t0 AND :t1
                ORDER BY ABS(EXTRACT(EPOCH FROM (timestamp - :ts))) ASC
                LIMIT 1
            """), {
                "dev_id": dev_id,
                "noise": list(NOISE_PROJECTS),
                "t0": ts - timedelta(minutes=30),
                "t1": ts + timedelta(minutes=30),
                "ts": ts
            }).fetchone()

            if browser_proj and browser_proj[0]:
                conn.execute(text("""
                    UPDATE activity_records
                    SET project_name = :proj, project_type = 'Development'
                    WHERE id = :id
                """), {"proj": browser_proj[0], "id": rec_id})
                ide_fixed += 1

        print(f"  Fixed {ide_fixed} IDE records using browser context.")

        # ----------------------------------------------------------------
        # Summary
        # ----------------------------------------------------------------
        remaining = conn.execute(text("""
            SELECT developer_id, project_name, COUNT(*) as cnt
            FROM activity_records
            WHERE LOWER(project_name) = ANY(:noise)
            GROUP BY developer_id, project_name
            ORDER BY developer_id, cnt DESC
        """), {"noise": list(NOISE_PROJECTS)}).fetchall()

        print("\nRemaining noise records (no browser context found):")
        for r in remaining:
            print(f"  {r[0]} | project={r[1]} | count={r[2]}")

        print("\nMigration complete.")


if __name__ == "__main__":
    run_migration()
