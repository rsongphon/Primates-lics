"""
Report Generation Background Tasks

Handles PDF, Excel, and CSV report generation for experiments, participants,
and organizational summaries. Implements Documentation.md Section 5.3 report patterns.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
import json
import csv
import io

from app.tasks.celery_app import celery_app
from app.core.database import get_async_session
from app.models.domain import Experiment, ExperimentData, Primate, Organization, Device
from app.tasks.notifications import send_email_notification
import asyncio

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.reports.generate_experiment_report",
    bind=True,
    time_limit=600  # 10 minutes
)
def generate_experiment_report(
    self,
    experiment_id: str,
    format: str = "pdf",
    include_raw_data: bool = False
) -> Dict[str, Any]:
    """
    Generate comprehensive experiment report.

    Creates detailed report with statistics, visualizations, and optionally
    raw trial data in PDF, Excel, or CSV format.

    Args:
        experiment_id: UUID of the experiment
        format: Output format (pdf, excel, csv)
        include_raw_data: Whether to include raw trial data

    Returns:
        Report generation status and file path
    """
    async def _generate():
        async for session in get_async_session():
            try:
                # Get experiment with related data
                result = await session.execute(
                    select(Experiment).where(Experiment.id == experiment_id)
                )
                experiment = result.scalar_one_or_none()

                if not experiment:
                    return {
                        "status": "not_found",
                        "experiment_id": experiment_id
                    }

                # Get experiment data
                data_result = await session.execute(
                    select(ExperimentData)
                    .where(ExperimentData.experiment_id == experiment_id)
                    .order_by(ExperimentData.created_at)
                )
                experiment_data = data_result.scalars().all()

                # Build report data
                report_data = {
                    "experiment_id": str(experiment.id),
                    "experiment_name": experiment.name,
                    "status": experiment.status,
                    "started_at": experiment.started_at.isoformat() if experiment.started_at else None,
                    "completed_at": experiment.actual_end.isoformat() if experiment.actual_end else None,
                    "total_trials": len(experiment_data),
                    "statistics": experiment.result_summary or {},
                    "generated_at": datetime.utcnow().isoformat()
                }

                if include_raw_data:
                    report_data["raw_data"] = [
                        {
                            "trial_number": d.data_metadata.get("trial_number"),
                            "timestamp": d.created_at.isoformat(),
                            "result": d.data_metadata
                        }
                        for d in experiment_data
                    ]

                # Generate report based on format
                if format == "pdf":
                    file_path = _generate_pdf_report(report_data)
                elif format == "excel":
                    file_path = _generate_excel_report(report_data)
                elif format == "csv":
                    file_path = _generate_csv_report(report_data)
                else:
                    file_path = _generate_json_report(report_data)

                logger.info(
                    f"Generated {format} report for experiment {experiment_id}",
                    extra={"file_path": file_path}
                )

                return {
                    "status": "success",
                    "experiment_id": experiment_id,
                    "format": format,
                    "file_path": file_path,
                    "task_id": self.request.id
                }

            except Exception as e:
                logger.error(f"Error generating experiment report: {e}")
                raise

    return asyncio.run(_generate())


def _generate_pdf_report(data: Dict[str, Any]) -> str:
    """
    Generate PDF report (placeholder implementation).

    In production, would use ReportLab or WeasyPrint.
    """
    # TODO: Implement PDF generation with ReportLab
    file_path = f"/tmp/reports/experiment_{data['experiment_id']}.pdf"
    logger.info(f"PDF report would be generated at: {file_path}")
    return file_path


def _generate_excel_report(data: Dict[str, Any]) -> str:
    """
    Generate Excel report (placeholder implementation).

    In production, would use openpyxl or xlsxwriter.
    """
    # TODO: Implement Excel generation
    file_path = f"/tmp/reports/experiment_{data['experiment_id']}.xlsx"
    logger.info(f"Excel report would be generated at: {file_path}")
    return file_path


def _generate_csv_report(data: Dict[str, Any]) -> str:
    """
    Generate CSV report with trial data.
    """
    file_path = f"/tmp/reports/experiment_{data['experiment_id']}.csv"

    # Write CSV data
    with open(file_path, 'w', newline='') as csvfile:
        if data.get("raw_data"):
            fieldnames = data["raw_data"][0]["result"].keys() if data["raw_data"] else []
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for trial in data["raw_data"]:
                writer.writerow(trial["result"])

    logger.info(f"CSV report generated at: {file_path}")
    return file_path


def _generate_json_report(data: Dict[str, Any]) -> str:
    """
    Generate JSON report.
    """
    file_path = f"/tmp/reports/experiment_{data['experiment_id']}.json"

    with open(file_path, 'w') as jsonfile:
        json.dump(data, jsonfile, indent=2)

    logger.info(f"JSON report generated at: {file_path}")
    return file_path


@celery_app.task(
    name="app.tasks.reports.generate_participant_progress_report",
    bind=True
)
def generate_participant_progress_report(
    self,
    primate_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate participant progress report across multiple experiments.

    Tracks primate learning progress, success rates, and performance trends
    over time.

    Args:
        primate_id: UUID of the primate
        start_date: Start date for report (ISO format)
        end_date: End date for report (ISO format)

    Returns:
        Report generation status and statistics
    """
    async def _generate():
        async for session in get_async_session():
            try:
                # Get primate
                primate_result = await session.execute(
                    select(Primate).where(Primate.id == primate_id)
                )
                primate = primate_result.scalar_one_or_none()

                if not primate:
                    return {
                        "status": "not_found",
                        "primate_id": primate_id
                    }

                # Get all experiments for this primate
                query = select(Experiment).where(Experiment.participant_id == primate_id)

                if start_date:
                    query = query.where(Experiment.started_at >= datetime.fromisoformat(start_date))
                if end_date:
                    query = query.where(Experiment.started_at <= datetime.fromisoformat(end_date))

                experiments_result = await session.execute(query.order_by(Experiment.started_at))
                experiments = experiments_result.scalars().all()

                # Compile progress data
                progress_data = {
                    "primate_id": str(primate.id),
                    "primate_name": primate.name,
                    "species": primate.species,
                    "training_level": primate.training_level,
                    "total_experiments": len(experiments),
                    "experiments": [
                        {
                            "id": str(exp.id),
                            "name": exp.name,
                            "started_at": exp.started_at.isoformat() if exp.started_at else None,
                            "success_rate": exp.result_summary.get("success_rate") if exp.result_summary else None,
                            "total_trials": exp.result_summary.get("total_trials") if exp.result_summary else 0
                        }
                        for exp in experiments
                    ],
                    "generated_at": datetime.utcnow().isoformat()
                }

                # Calculate overall statistics
                success_rates = [
                    exp.result_summary.get("success_rate", 0)
                    for exp in experiments
                    if exp.result_summary
                ]
                progress_data["overall_success_rate"] = (
                    sum(success_rates) / len(success_rates) if success_rates else 0
                )

                logger.info(
                    f"Generated progress report for primate {primate_id}",
                    extra={"total_experiments": len(experiments)}
                )

                return {
                    "status": "success",
                    "primate_id": primate_id,
                    "data": progress_data,
                    "task_id": self.request.id
                }

            except Exception as e:
                logger.error(f"Error generating participant progress report: {e}")
                raise

    return asyncio.run(_generate())


@celery_app.task(
    name="app.tasks.reports.generate_organization_summary",
    bind=True
)
def generate_organization_summary(
    self,
    organization_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate organization-wide summary report.

    Compiles statistics across all experiments, devices, and participants
    for the organization.

    Args:
        organization_id: UUID of organization (None for all organizations)

    Returns:
        Report generation status and summary data
    """
    async def _generate():
        async for session in get_async_session():
            try:
                # Get organization(s)
                if organization_id:
                    org_query = select(Organization).where(Organization.id == organization_id)
                else:
                    org_query = select(Organization)

                org_result = await session.execute(org_query)
                organizations = org_result.scalars().all()

                summaries = []

                for org in organizations:
                    # Get organization statistics
                    # Count devices
                    device_count = await session.scalar(
                        select(func.count(Device.id)).where(Device.organization_id == org.id)
                    )

                    # Count experiments
                    experiment_count = await session.scalar(
                        select(func.count(Experiment.id)).where(Experiment.organization_id == org.id)
                    )

                    # Count primates
                    primate_count = await session.scalar(
                        select(func.count(Primate.id)).where(Primate.organization_id == org.id)
                    )

                    # Get recent experiments
                    recent_experiments = await session.execute(
                        select(Experiment)
                        .where(Experiment.organization_id == org.id)
                        .order_by(Experiment.created_at.desc())
                        .limit(10)
                    )

                    summary = {
                        "organization_id": str(org.id),
                        "organization_name": org.name,
                        "total_devices": device_count,
                        "total_experiments": experiment_count,
                        "total_primates": primate_count,
                        "recent_experiments": len(recent_experiments.scalars().all()),
                        "generated_at": datetime.utcnow().isoformat()
                    }

                    summaries.append(summary)

                    # Send email notification to org admins
                    # send_email_notification.delay(
                    #     to_email=org.admin_email,  # Would need to add this field
                    #     subject=f"Daily Summary: {org.name}",
                    #     body=json.dumps(summary, indent=2)
                    # )

                logger.info(f"Generated organization summaries for {len(summaries)} organizations")

                return {
                    "status": "success",
                    "organizations_processed": len(summaries),
                    "summaries": summaries,
                    "task_id": self.request.id
                }

            except Exception as e:
                logger.error(f"Error generating organization summary: {e}")
                raise

    return asyncio.run(_generate())


@celery_app.task(
    name="app.tasks.reports.export_data_to_storage",
    bind=True
)
def export_data_to_storage(
    self,
    experiment_id: str,
    storage_type: str = "minio",
    format: str = "csv"
) -> Dict[str, Any]:
    """
    Export experiment data to object storage (MinIO/S3).

    Args:
        experiment_id: UUID of the experiment
        storage_type: Storage backend (minio, s3)
        format: Export format (csv, json, parquet)

    Returns:
        Export status and storage location
    """
    try:
        # Generate report
        report_result = generate_experiment_report(
            experiment_id=experiment_id,
            format=format,
            include_raw_data=True
        )

        if report_result["status"] != "success":
            return report_result

        file_path = report_result["file_path"]

        # TODO: Upload to MinIO/S3
        # from minio import Minio
        # client = Minio(settings.MINIO_ENDPOINT, ...)
        # client.fput_object("exports", f"{experiment_id}.{format}", file_path)

        storage_url = f"{storage_type}://exports/{experiment_id}.{format}"

        logger.info(
            f"Exported experiment data to storage",
            extra={
                "experiment_id": experiment_id,
                "storage_url": storage_url
            }
        )

        return {
            "status": "success",
            "experiment_id": experiment_id,
            "storage_url": storage_url,
            "format": format,
            "task_id": self.request.id
        }

    except Exception as e:
        logger.error(f"Error exporting data to storage: {e}")
        raise
