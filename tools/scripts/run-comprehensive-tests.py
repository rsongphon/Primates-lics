#!/usr/bin/env python3
"""
LICS Comprehensive Test Orchestrator

Master test orchestrator that provides a unified interface to run all LICS
validation and testing suites with intelligent scheduling and reporting.

Usage:
    python run-comprehensive-tests.py [--suite all|infrastructure|database|messaging|integration]
                                      [--mode quick|standard|benchmark|stress]
                                      [--format text|json|html] [--output results/]
                                      [--parallel] [--continuous] [--report]

Features:
    - Unified test execution interface
    - Intelligent test scheduling and dependencies
    - Comprehensive reporting with multiple formats
    - Performance benchmarking and trending
    - Continuous testing mode
    - Test result aggregation and analysis
    - HTML dashboard generation
    - CI/CD integration support
"""

import argparse
import asyncio
import json
import os
import sys
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import webbrowser
import tempfile
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('comprehensive-tests.log')
    ]
)
logger = logging.getLogger(__name__)

class ComprehensiveTestOrchestrator:
    """Master test orchestrator for all LICS validation and testing."""

    def __init__(self, mode: str = "standard", parallel: bool = False,
                 output_dir: Optional[str] = None):
        """
        Initialize the test orchestrator.

        Args:
            mode: Test mode (quick, standard, benchmark, stress)
            parallel: Enable parallel test execution
            output_dir: Directory for test outputs
        """
        self.mode = mode
        self.parallel = parallel
        self.start_time = time.time()
        self.project_root = Path(__file__).parent.parent.parent

        # Set up output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.project_root / "test-results" / datetime.now().strftime("%Y%m%d_%H%M%S")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Test suite configurations
        self.test_suites = {
            'infrastructure': {
                'script': 'validate-infrastructure.py',
                'name': 'Infrastructure Validation',
                'description': 'Validates Docker services, networking, and SSL certificates',
                'required': True,
                'timeout': 300,
                'args': self._get_infrastructure_args()
            },
            'database': {
                'script': 'test-database-suite.py',
                'name': 'Database Test Suite',
                'description': 'Tests PostgreSQL, Redis, InfluxDB, and PgBouncer',
                'required': True,
                'timeout': 600,
                'args': self._get_database_args()
            },
            'messaging': {
                'script': 'test-messaging-suite.py',
                'name': 'Messaging Test Suite',
                'description': 'Tests MQTT, Redis Streams/Pub-Sub, and MinIO',
                'required': True,
                'timeout': 400,
                'args': self._get_messaging_args()
            },
            'integration': {
                'script': 'test-system-integration.py',
                'name': 'System Integration Test',
                'description': 'End-to-end integration and cross-service testing',
                'required': False,
                'timeout': 800,
                'args': self._get_integration_args()
            }
        }

        self.results = {}
        self.execution_summary = {
            'start_time': datetime.now().isoformat(),
            'mode': mode,
            'parallel': parallel,
            'test_suites_run': [],
            'total_duration': 0,
            'overall_healthy': False
        }

    def _get_infrastructure_args(self) -> List[str]:
        """Get arguments for infrastructure validation."""
        args = ['--format', 'json']
        if self.mode == 'quick':
            args.append('--quick')
        return args

    def _get_database_args(self) -> List[str]:
        """Get arguments for database testing."""
        args = ['--format', 'json']
        if self.mode in ['benchmark', 'stress']:
            args.append('--benchmark')
        if self.mode == 'stress':
            args.append('--stress')
        return args

    def _get_messaging_args(self) -> List[str]:
        """Get arguments for messaging testing."""
        args = ['--format', 'json']
        if self.mode in ['benchmark', 'stress']:
            args.append('--benchmark')
        if self.mode == 'stress':
            args.append('--load-test')
        return args

    def _get_integration_args(self) -> List[str]:
        """Get arguments for integration testing."""
        args = ['--format', 'json']
        if self.mode == 'quick':
            args.append('--quick')
        if self.mode in ['benchmark', 'stress']:
            args.append('--benchmark')
        if self.mode == 'stress':
            args.append('--stress')
        if self.parallel:
            args.append('--parallel')
        return args

    def print_banner(self):
        """Print test orchestrator banner."""
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    LICS COMPREHENSIVE TEST ORCHESTRATOR                      ║
║                                                                              ║
║  Systematic validation of all LICS infrastructure and functionality         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        print(banner)
        print(f"🕐 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔧 Test Mode: {self.mode.upper()}")
        print(f"🚀 Parallel Execution: {'Enabled' if self.parallel else 'Disabled'}")
        print(f"📁 Output Directory: {self.output_dir}")
        print("=" * 80)

    async def run_test_suite(self, suite_name: str, suite_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run an individual test suite."""
        logger.info(f"🧪 Running {suite_config['name']}...")
        print(f"\n🧪 Running {suite_config['name']}")
        print(f"   Description: {suite_config['description']}")

        result = {
            'name': suite_config['name'],
            'suite': suite_name,
            'start_time': datetime.now().isoformat(),
            'duration_seconds': 0,
            'healthy': False,
            'output_file': None,
            'error': None
        }

        start_time = time.time()

        try:
            # Prepare command
            script_path = self.project_root / "tools/scripts" / suite_config['script']
            cmd = [sys.executable, str(script_path)] + suite_config['args']

            # Set up output file
            output_file = self.output_dir / f"{suite_name}_results.json"
            cmd.extend(['--output', str(output_file)])

            # Run the test suite
            print(f"   Command: {' '.join(cmd[1:])}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.project_root
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=suite_config['timeout']
                )

                result['duration_seconds'] = round(time.time() - start_time, 2)

                if process.returncode == 0:
                    result['healthy'] = True
                    result['output_file'] = str(output_file)

                    # Load detailed results if available
                    if output_file.exists():
                        try:
                            with open(output_file, 'r') as f:
                                detailed_results = json.load(f)
                                result['detailed_results'] = detailed_results
                                result['healthy'] = detailed_results.get('overall_healthy', True)
                        except json.JSONDecodeError:
                            pass

                    print(f"   ✅ Completed successfully in {result['duration_seconds']}s")
                else:
                    result['error'] = stderr.decode() if stderr else 'Unknown error'
                    print(f"   ❌ Failed: {result['error']}")

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                result['error'] = f"Test suite timed out after {suite_config['timeout']} seconds"
                result['duration_seconds'] = suite_config['timeout']
                print(f"   ⏰ Timed out after {suite_config['timeout']}s")

        except Exception as e:
            result['error'] = str(e)
            result['duration_seconds'] = round(time.time() - start_time, 2)
            print(f"   ❌ Error: {e}")

        result['end_time'] = datetime.now().isoformat()
        return result

    async def run_test_suites(self, suites_to_run: List[str]) -> Dict[str, Any]:
        """Run selected test suites."""
        suite_results = {}

        if self.parallel and len(suites_to_run) > 1:
            # Run independent suites in parallel
            print("\n🚀 Running test suites in parallel...")

            # For now, run all in parallel (could add dependency logic)
            tasks = []
            for suite_name in suites_to_run:
                if suite_name in self.test_suites:
                    task = self.run_test_suite(suite_name, self.test_suites[suite_name])
                    tasks.append((suite_name, task))

            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

            for (suite_name, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    suite_results[suite_name] = {
                        'name': self.test_suites[suite_name]['name'],
                        'healthy': False,
                        'error': str(result)
                    }
                else:
                    suite_results[suite_name] = result

        else:
            # Run suites sequentially
            print("\n📋 Running test suites sequentially...")

            for suite_name in suites_to_run:
                if suite_name in self.test_suites:
                    suite_results[suite_name] = await self.run_test_suite(
                        suite_name, self.test_suites[suite_name]
                    )

        return suite_results

    def analyze_results(self, suite_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test results and generate summary."""
        total_suites = len(suite_results)
        healthy_suites = sum(1 for result in suite_results.values() if result.get('healthy', False))
        total_duration = sum(result.get('duration_seconds', 0) for result in suite_results.values())

        analysis = {
            'execution_summary': {
                'total_suites': total_suites,
                'healthy_suites': healthy_suites,
                'failed_suites': total_suites - healthy_suites,
                'success_rate': round((healthy_suites / total_suites * 100), 2) if total_suites > 0 else 0,
                'total_duration': round(total_duration, 2),
                'overall_healthy': healthy_suites == total_suites
            },
            'suite_summary': {},
            'recommendations': [],
            'failed_suites': []
        }

        # Analyze individual suites
        for suite_name, result in suite_results.items():
            suite_analysis = {
                'healthy': result.get('healthy', False),
                'duration': result.get('duration_seconds', 0),
                'key_metrics': {}
            }

            # Extract key metrics from detailed results
            if 'detailed_results' in result:
                detailed = result['detailed_results']

                if suite_name == 'infrastructure':
                    if 'summary' in detailed:
                        suite_analysis['key_metrics'] = {
                            'services_healthy': f"{detailed['summary'].get('healthy_checks', 0)}/{detailed['summary'].get('total_checks', 0)}",
                            'success_rate': f"{detailed['summary'].get('success_rate', 0)}%"
                        }

                elif suite_name == 'database':
                    if 'summary' in detailed:
                        suite_analysis['key_metrics'] = {
                            'databases_healthy': f"{detailed['summary'].get('healthy_databases', 0)}/{detailed['summary'].get('total_databases', 0)}",
                            'success_rate': f"{detailed['summary'].get('success_rate', 0)}%"
                        }

                elif suite_name == 'messaging':
                    if 'summary' in detailed:
                        suite_analysis['key_metrics'] = {
                            'components_healthy': f"{detailed['summary'].get('healthy_components', 0)}/{detailed['summary'].get('total_components', 0)}",
                            'success_rate': f"{detailed['summary'].get('success_rate', 0)}%"
                        }

                elif suite_name == 'integration':
                    if 'summary' in detailed:
                        suite_analysis['key_metrics'] = {
                            'overall_success_rate': f"{detailed['summary'].get('overall_success_rate', 0)}%"
                        }

            analysis['suite_summary'][suite_name] = suite_analysis

            # Track failed suites
            if not result.get('healthy', False):
                analysis['failed_suites'].append({
                    'suite': suite_name,
                    'name': result.get('name', suite_name),
                    'error': result.get('error', 'Unknown error')
                })

        # Generate recommendations
        if not analysis['execution_summary']['overall_healthy']:
            if 'infrastructure' in analysis['failed_suites']:
                analysis['recommendations'].append(
                    "Infrastructure validation failed - check Docker services and network connectivity"
                )
            if 'database' in analysis['failed_suites']:
                analysis['recommendations'].append(
                    "Database tests failed - verify PostgreSQL, Redis, and InfluxDB are properly configured"
                )
            if 'messaging' in analysis['failed_suites']:
                analysis['recommendations'].append(
                    "Messaging tests failed - check MQTT broker, Redis Streams, and MinIO storage"
                )
            if 'integration' in analysis['failed_suites']:
                analysis['recommendations'].append(
                    "Integration tests failed - review cross-service communication and data flows"
                )

        return analysis

    def generate_text_report(self, suite_results: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate comprehensive text report."""
        output = []
        output.append("=" * 100)
        output.append("LICS COMPREHENSIVE TEST EXECUTION REPORT")
        output.append("=" * 100)
        output.append(f"Timestamp: {datetime.now().isoformat()}")
        output.append(f"Test Mode: {self.mode.upper()}")
        output.append(f"Parallel Execution: {'Enabled' if self.parallel else 'Disabled'}")
        output.append(f"Total Duration: {analysis['execution_summary']['total_duration']}s")
        output.append(f"Overall Status: {'✅ HEALTHY' if analysis['execution_summary']['overall_healthy'] else '❌ UNHEALTHY'}")
        output.append("")

        # Execution Summary
        summary = analysis['execution_summary']
        output.append("EXECUTION SUMMARY:")
        output.append("-" * 50)
        output.append(f"Test Suites Run: {summary['total_suites']}")
        output.append(f"Healthy Suites: {summary['healthy_suites']}")
        output.append(f"Failed Suites: {summary['failed_suites']}")
        output.append(f"Success Rate: {summary['success_rate']}%")
        output.append("")

        # Individual Suite Results
        output.append("INDIVIDUAL SUITE RESULTS:")
        output.append("-" * 50)
        for suite_name, result in suite_results.items():
            status_icon = "✅" if result.get('healthy', False) else "❌"
            output.append(f"{status_icon} {result.get('name', suite_name)}")
            output.append(f"   Duration: {result.get('duration_seconds', 0)}s")

            # Key metrics
            suite_summary = analysis['suite_summary'].get(suite_name, {})
            if suite_summary.get('key_metrics'):
                output.append("   Key Metrics:")
                for metric, value in suite_summary['key_metrics'].items():
                    output.append(f"     {metric}: {value}")

            # Error information
            if result.get('error'):
                output.append(f"   Error: {result['error']}")

            # Output file
            if result.get('output_file'):
                output.append(f"   Detailed Results: {result['output_file']}")

            output.append("")

        # Failed Suites Detail
        if analysis['failed_suites']:
            output.append("FAILED SUITES ANALYSIS:")
            output.append("-" * 50)
            for failed_suite in analysis['failed_suites']:
                output.append(f"❌ {failed_suite['name']}")
                output.append(f"   Error: {failed_suite['error']}")
                output.append("")

        # Recommendations
        if analysis['recommendations']:
            output.append("RECOMMENDATIONS:")
            output.append("-" * 50)
            for i, recommendation in enumerate(analysis['recommendations'], 1):
                output.append(f"{i}. {recommendation}")
            output.append("")

        # Performance Summary (if benchmark mode)
        if self.mode in ['benchmark', 'stress']:
            output.append("PERFORMANCE SUMMARY:")
            output.append("-" * 50)
            for suite_name, result in suite_results.items():
                if 'detailed_results' in result and 'performance' in result.get('detailed_results', {}):
                    output.append(f"{result.get('name', suite_name)}:")
                    perf_data = result['detailed_results']['performance']
                    for metric, value in perf_data.items():
                        output.append(f"  {metric}: {value}")
                    output.append("")

        # Test Files and Outputs
        output.append("TEST OUTPUTS:")
        output.append("-" * 50)
        output.append(f"Output Directory: {self.output_dir}")
        output.append("Generated Files:")
        for suite_name, result in suite_results.items():
            if result.get('output_file'):
                output.append(f"  - {suite_name}: {Path(result['output_file']).name}")
        output.append("")

        return "\n".join(output)

    def generate_html_report(self, suite_results: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate HTML dashboard report."""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LICS Comprehensive Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .status-healthy {{ color: #28a745; font-weight: bold; }}
        .status-unhealthy {{ color: #dc3545; font-weight: bold; }}
        .card {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }}
        .metric-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; }}
        .suite-result {{ border-left: 4px solid #ddd; padding: 15px; margin-bottom: 15px; background: #f8f9fa; }}
        .suite-healthy {{ border-left-color: #28a745; }}
        .suite-failed {{ border-left-color: #dc3545; }}
        .progress-bar {{ width: 100%; height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; }}
        .progress-fill {{ height: 100%; background: linear-gradient(90deg, #28a745, #20c997); transition: width 0.3s ease; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
        .timestamp {{ color: #6c757d; font-size: 0.9em; }}
        .recommendations {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 15px; }}
        .recommendation-item {{ margin-bottom: 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 LICS Comprehensive Test Report</h1>
            <p class="timestamp">Generated: {timestamp}</p>
            <p>Test Mode: <strong>{mode}</strong> | Parallel: <strong>{parallel}</strong></p>
        </div>

        <div class="card">
            <h2>📊 Execution Summary</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>Overall Status</h3>
                    <div class="{overall_status_class}">{overall_status}</div>
                </div>
                <div class="metric-card">
                    <h3>Success Rate</h3>
                    <div style="font-size: 1.5em; font-weight: bold;">{success_rate}%</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {success_rate}%;"></div>
                    </div>
                </div>
                <div class="metric-card">
                    <h3>Total Duration</h3>
                    <div style="font-size: 1.5em; font-weight: bold;">{total_duration}s</div>
                </div>
                <div class="metric-card">
                    <h3>Suites Status</h3>
                    <div>{healthy_suites}/{total_suites} Healthy</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>🧪 Test Suite Results</h2>
            {suite_results_html}
        </div>

        {recommendations_html}

        <div class="card">
            <h2>📁 Test Outputs</h2>
            <p><strong>Output Directory:</strong> {output_dir}</p>
            <table>
                <thead>
                    <tr>
                        <th>Test Suite</th>
                        <th>Output File</th>
                        <th>Status</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
                    {output_files_html}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
        """

        # Prepare template variables
        summary = analysis['execution_summary']

        # Suite results HTML
        suite_results_html = ""
        for suite_name, result in suite_results.items():
            status_class = "suite-healthy" if result.get('healthy', False) else "suite-failed"
            status_text = "✅ PASSED" if result.get('healthy', False) else "❌ FAILED"

            suite_html = f"""
            <div class="suite-result {status_class}">
                <h3>{result.get('name', suite_name)} - {status_text}</h3>
                <p><strong>Duration:</strong> {result.get('duration_seconds', 0)}s</p>
            """

            # Add key metrics
            suite_summary = analysis['suite_summary'].get(suite_name, {})
            if suite_summary.get('key_metrics'):
                suite_html += "<p><strong>Key Metrics:</strong></p><ul>"
                for metric, value in suite_summary['key_metrics'].items():
                    suite_html += f"<li>{metric}: {value}</li>"
                suite_html += "</ul>"

            # Add error if failed
            if result.get('error'):
                suite_html += f"<p><strong>Error:</strong> {result['error']}</p>"

            suite_html += "</div>"
            suite_results_html += suite_html

        # Recommendations HTML
        recommendations_html = ""
        if analysis['recommendations']:
            recommendations_html = """
            <div class="card">
                <h2>💡 Recommendations</h2>
                <div class="recommendations">
            """
            for i, rec in enumerate(analysis['recommendations'], 1):
                recommendations_html += f'<div class="recommendation-item">{i}. {rec}</div>'
            recommendations_html += "</div></div>"

        # Output files HTML
        output_files_html = ""
        for suite_name, result in suite_results.items():
            status_badge = "✅" if result.get('healthy', False) else "❌"
            output_file = Path(result.get('output_file', '')).name if result.get('output_file') else 'N/A'
            output_files_html += f"""
            <tr>
                <td>{result.get('name', suite_name)}</td>
                <td>{output_file}</td>
                <td>{status_badge}</td>
                <td>{result.get('duration_seconds', 0)}s</td>
            </tr>
            """

        # Fill template
        html_content = html_template.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            mode=self.mode.upper(),
            parallel='Enabled' if self.parallel else 'Disabled',
            overall_status='✅ HEALTHY' if summary['overall_healthy'] else '❌ UNHEALTHY',
            overall_status_class='status-healthy' if summary['overall_healthy'] else 'status-unhealthy',
            success_rate=summary['success_rate'],
            total_duration=summary['total_duration'],
            healthy_suites=summary['healthy_suites'],
            total_suites=summary['total_suites'],
            suite_results_html=suite_results_html,
            recommendations_html=recommendations_html,
            output_dir=self.output_dir,
            output_files_html=output_files_html
        )

        return html_content

    def save_results(self, suite_results: Dict[str, Any], analysis: Dict[str, Any],
                     format_type: str = "text") -> str:
        """Save comprehensive test results."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format_type == "json":
            # Save comprehensive JSON results
            comprehensive_results = {
                'execution_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'mode': self.mode,
                    'parallel': self.parallel,
                    'output_directory': str(self.output_dir)
                },
                'suite_results': suite_results,
                'analysis': analysis
            }

            json_file = self.output_dir / f"comprehensive_results_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump(comprehensive_results, f, indent=2)
            return str(json_file)

        elif format_type == "html":
            html_content = self.generate_html_report(suite_results, analysis)
            html_file = self.output_dir / f"test_report_{timestamp}.html"
            with open(html_file, 'w') as f:
                f.write(html_content)
            return str(html_file)

        else:  # text
            text_content = self.generate_text_report(suite_results, analysis)
            text_file = self.output_dir / f"test_report_{timestamp}.txt"
            with open(text_file, 'w') as f:
                f.write(text_content)
            return str(text_file)

    async def run_comprehensive_tests(self, suites_to_run: List[str],
                                      generate_report: bool = True) -> Dict[str, Any]:
        """Run comprehensive tests and generate reports."""
        self.print_banner()

        # Validate suites
        valid_suites = [suite for suite in suites_to_run if suite in self.test_suites]
        if not valid_suites:
            print(f"❌ No valid test suites specified. Available: {', '.join(self.test_suites.keys())}")
            return {}

        print(f"📋 Test Suites to Run: {', '.join(valid_suites)}")
        print(f"📁 Results will be saved to: {self.output_dir}")

        # Run test suites
        suite_results = await self.run_test_suites(valid_suites)

        # Analyze results
        analysis = self.analyze_results(suite_results)

        # Update execution summary
        self.execution_summary.update({
            'end_time': datetime.now().isoformat(),
            'total_duration': round(time.time() - self.start_time, 2),
            'test_suites_run': valid_suites,
            'overall_healthy': analysis['execution_summary']['overall_healthy']
        })

        # Print summary
        print("\n" + "=" * 80)
        print("📊 EXECUTION SUMMARY")
        print("=" * 80)
        summary = analysis['execution_summary']
        print(f"Overall Status: {'✅ HEALTHY' if summary['overall_healthy'] else '❌ UNHEALTHY'}")
        print(f"Success Rate: {summary['success_rate']}%")
        print(f"Total Duration: {summary['total_duration']}s")
        print(f"Healthy Suites: {summary['healthy_suites']}/{summary['total_suites']}")

        if analysis['failed_suites']:
            print(f"\n❌ Failed Suites:")
            for failed in analysis['failed_suites']:
                print(f"   - {failed['name']}: {failed['error']}")

        # Generate reports
        if generate_report:
            print(f"\n📄 Generating comprehensive reports...")

            # Save results in multiple formats
            json_file = self.save_results(suite_results, analysis, "json")
            text_file = self.save_results(suite_results, analysis, "text")
            html_file = self.save_results(suite_results, analysis, "html")

            print(f"   📄 Text Report: {text_file}")
            print(f"   📊 HTML Dashboard: {html_file}")
            print(f"   📋 JSON Results: {json_file}")

            # Optionally open HTML report
            try:
                if os.getenv('DISPLAY') or os.name == 'nt':  # Unix with display or Windows
                    open_report = input("\n🌐 Open HTML report in browser? [y/N]: ").lower().strip()
                    if open_report == 'y':
                        webbrowser.open(f"file://{Path(html_file).absolute()}")
            except:
                pass

        print(f"\n🏁 Comprehensive testing completed!")
        print(f"📁 All results saved to: {self.output_dir}")

        return {
            'suite_results': suite_results,
            'analysis': analysis,
            'execution_summary': self.execution_summary,
            'output_directory': str(self.output_dir)
        }

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='LICS Comprehensive Test Orchestrator')
    parser.add_argument('--suite',
                       choices=['all', 'infrastructure', 'database', 'messaging', 'integration'],
                       default='all',
                       help='Test suite to run (default: all)')
    parser.add_argument('--mode',
                       choices=['quick', 'standard', 'benchmark', 'stress'],
                       default='standard',
                       help='Test execution mode (default: standard)')
    parser.add_argument('--format',
                       choices=['text', 'json', 'html'],
                       default='text',
                       help='Primary output format (default: text)')
    parser.add_argument('--output', '-o',
                       help='Output directory for results (default: auto-generated)')
    parser.add_argument('--parallel', action='store_true',
                       help='Enable parallel test execution')
    parser.add_argument('--no-report', action='store_true',
                       help='Skip comprehensive report generation')
    parser.add_argument('--continuous', action='store_true',
                       help='Run tests continuously (for monitoring)')
    parser.add_argument('--interval', type=int, default=3600,
                       help='Interval for continuous testing in seconds (default: 3600)')
    parser.add_argument('--exit-code', action='store_true',
                       help='Exit with non-zero code if tests fail')

    args = parser.parse_args()

    # Determine suites to run
    if args.suite == 'all':
        suites_to_run = ['infrastructure', 'database', 'messaging', 'integration']
    else:
        suites_to_run = [args.suite]

    try:
        if args.continuous:
            print(f"🔄 Starting continuous testing mode (interval: {args.interval}s)")
            print("Press Ctrl+C to stop")

            run_count = 0
            while True:
                run_count += 1
                print(f"\n{'='*80}")
                print(f"🔄 Continuous Test Run #{run_count}")
                print(f"{'='*80}")

                orchestrator = ComprehensiveTestOrchestrator(
                    mode=args.mode,
                    parallel=args.parallel,
                    output_dir=args.output
                )

                results = await orchestrator.run_comprehensive_tests(
                    suites_to_run,
                    generate_report=not args.no_report
                )

                if not results.get('execution_summary', {}).get('overall_healthy', False):
                    print(f"⚠️  Tests failed in run #{run_count}")

                print(f"😴 Waiting {args.interval}s until next run...")
                await asyncio.sleep(args.interval)

        else:
            # Single test run
            orchestrator = ComprehensiveTestOrchestrator(
                mode=args.mode,
                parallel=args.parallel,
                output_dir=args.output
            )

            results = await orchestrator.run_comprehensive_tests(
                suites_to_run,
                generate_report=not args.no_report
            )

            # Exit code based on results
            if args.exit_code:
                overall_healthy = results.get('execution_summary', {}).get('overall_healthy', False)
                sys.exit(0 if overall_healthy else 1)

    except KeyboardInterrupt:
        print("\n⚠️ Test execution cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Comprehensive test orchestrator failed: {e}")
        logger.exception("Test orchestrator failed with exception")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())