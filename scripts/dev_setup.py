#!/usr/bin/env python3
"""
Development setup and utility script for AI Mail MCP.

This script helps developers set up their development environment,
run tests, and perform common development tasks.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


class DevSetup:
    """Development environment setup and management."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.venv_path = project_root / "venv"
        self.src_path = project_root / "src"
        self.tests_path = project_root / "tests"
        
    def run_command(self, command: List[str], cwd: Optional[Path] = None) -> int:
        """Run a command and return exit code."""
        cwd = cwd or self.project_root
        print(f"🔧 Running: {' '.join(command)}")
        
        try:
            result = subprocess.run(command, cwd=cwd, check=False)
            return result.returncode
        except FileNotFoundError:
            print(f"❌ Command not found: {command[0]}")
            return 1
    
    def check_python_version(self) -> bool:
        """Check if Python version meets requirements."""
        major, minor = sys.version_info[:2]
        
        if major >= 3 and minor >= 8:
            print(f"✅ Python {major}.{minor} is supported")
            return True
        else:
            print(f"❌ Python {major}.{minor} is not supported (requires 3.8+)")
            return False
    
    def create_virtual_environment(self) -> bool:
        """Create a Python virtual environment."""
        if self.venv_path.exists():
            print(f"✅ Virtual environment already exists: {self.venv_path}")
            return True
        
        print(f"🚀 Creating virtual environment: {self.venv_path}")
        result = self.run_command([sys.executable, "-m", "venv", str(self.venv_path)])
        
        if result == 0:
            print("✅ Virtual environment created successfully")
            return True
        else:
            print("❌ Failed to create virtual environment")
            return False
    
    def get_pip_command(self) -> List[str]:
        """Get the pip command for the virtual environment."""
        if os.name == "nt":  # Windows
            return [str(self.venv_path / "Scripts" / "pip.exe")]
        else:  # Unix-like
            return [str(self.venv_path / "bin" / "pip")]
    
    def get_python_command(self) -> List[str]:
        """Get the Python command for the virtual environment."""
        if os.name == "nt":  # Windows
            return [str(self.venv_path / "Scripts" / "python.exe")]
        else:  # Unix-like
            return [str(self.venv_path / "bin" / "python")]
    
    def install_dependencies(self, dev: bool = True) -> bool:
        """Install project dependencies."""
        pip_cmd = self.get_pip_command()
        
        # Upgrade pip first
        print("📦 Upgrading pip...")
        self.run_command(pip_cmd + ["install", "--upgrade", "pip"])
        
        # Install project in development mode
        if dev:
            print("📦 Installing development dependencies...")
            result = self.run_command(pip_cmd + ["install", "-e", ".[dev]"])
        else:
            print("📦 Installing production dependencies...")
            result = self.run_command(pip_cmd + ["install", "-e", "."])
        
        if result == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print("❌ Failed to install dependencies")
            return False
    
    def setup_pre_commit(self) -> bool:
        """Set up pre-commit hooks."""
        python_cmd = self.get_python_command()
        
        print("🪝 Setting up pre-commit hooks...")
        result = self.run_command(python_cmd + ["-m", "pre_commit", "install"])
        
        if result == 0:
            print("✅ Pre-commit hooks installed")
            return True
        else:
            print("❌ Failed to install pre-commit hooks")
            return False
    
    def run_tests(self, coverage: bool = True, verbose: bool = True) -> bool:
        """Run the test suite."""
        python_cmd = self.get_python_command()
        
        test_args = ["-m", "pytest"]
        
        if verbose:
            test_args.append("-v")
        
        if coverage:
            test_args.extend(["--cov=ai_mail_mcp", "--cov-report=term-missing"])
        
        test_args.append("tests/")
        
        print("🧪 Running test suite...")
        result = self.run_command(python_cmd + test_args)
        
        if result == 0:
            print("✅ All tests passed")
            return True
        else:
            print("❌ Some tests failed")
            return False
    
    def run_linting(self) -> bool:
        """Run code linting and formatting checks."""
        python_cmd = self.get_python_command()
        
        # Check formatting with black
        print("🎨 Checking code formatting with black...")
        black_result = self.run_command(python_cmd + ["-m", "black", "--check", "src", "tests"])
        
        # Check import sorting with isort
        print("📚 Checking import sorting with isort...")
        isort_result = self.run_command(python_cmd + ["-m", "isort", "--check-only", "src", "tests"])
        
        # Run flake8 linting
        print("🔍 Running flake8 linting...")
        flake8_result = self.run_command(python_cmd + ["-m", "flake8", "src", "tests"])
        
        # Run mypy type checking
        print("🔎 Running mypy type checking...")
        mypy_result = self.run_command(python_cmd + ["-m", "mypy", "src"])
        
        all_passed = all(result == 0 for result in [black_result, isort_result, flake8_result, mypy_result])
        
        if all_passed:
            print("✅ All linting checks passed")
            return True
        else:
            print("❌ Some linting checks failed")
            return False
    
    def format_code(self) -> bool:
        """Format code with black and isort."""
        python_cmd = self.get_python_command()
        
        print("🎨 Formatting code with black...")
        black_result = self.run_command(python_cmd + ["-m", "black", "src", "tests"])
        
        print("📚 Sorting imports with isort...")
        isort_result = self.run_command(python_cmd + ["-m", "isort", "src", "tests"])
        
        if black_result == 0 and isort_result == 0:
            print("✅ Code formatted successfully")
            return True
        else:
            print("❌ Code formatting failed")
            return False
    
    def run_security_checks(self) -> bool:
        """Run security checks."""
        python_cmd = self.get_python_command()
        
        print("🔒 Running security checks with bandit...")
        bandit_result = self.run_command(python_cmd + ["-m", "bandit", "-r", "src/"])
        
        print("🛡️ Checking for known vulnerabilities with safety...")
        safety_result = self.run_command(python_cmd + ["-m", "safety", "check"])
        
        if bandit_result == 0 and safety_result == 0:
            print("✅ Security checks passed")
            return True
        else:
            print("❌ Security checks found issues")
            return False
    
    def run_performance_tests(self) -> bool:
        """Run performance benchmarks."""
        python_cmd = self.get_python_command()
        
        print("⚡ Running performance benchmarks...")
        result = self.run_command(python_cmd + ["scripts/benchmark.py"])
        
        if result == 0:
            print("✅ Performance benchmarks passed")
            return True
        else:
            print("❌ Performance benchmarks failed")
            return False
    
    def build_package(self) -> bool:
        """Build the Python package."""
        python_cmd = self.get_python_command()
        
        print("📦 Building package...")
        result = self.run_command(python_cmd + ["-m", "build"])
        
        if result == 0:
            print("✅ Package built successfully")
            return True
        else:
            print("❌ Package build failed")
            return False
    
    def clean_build_artifacts(self) -> bool:
        """Clean build artifacts and cache files."""
        import shutil
        
        artifacts_to_clean = [
            "build/",
            "dist/",
            "*.egg-info/",
            "__pycache__/",
            ".pytest_cache/",
            ".coverage",
            "htmlcov/",
            ".mypy_cache/"
        ]
        
        print("🧹 Cleaning build artifacts...")
        
        for pattern in artifacts_to_clean:
            if pattern.endswith("/"):
                # Directory
                for path in self.project_root.glob(f"**/{pattern}"):
                    if path.is_dir():
                        print(f"   Removing {path}")
                        shutil.rmtree(path)
            else:
                # File
                for path in self.project_root.glob(f"**/{pattern}"):
                    if path.is_file():
                        print(f"   Removing {path}")
                        path.unlink()
        
        print("✅ Build artifacts cleaned")
        return True
    
    def setup_development_environment(self) -> bool:
        """Set up complete development environment."""
        print("🚀 Setting up AI Mail MCP development environment")
        print("=" * 50)
        
        steps = [
            ("Check Python version", self.check_python_version),
            ("Create virtual environment", self.create_virtual_environment),
            ("Install dependencies", lambda: self.install_dependencies(dev=True)),
            ("Setup pre-commit hooks", self.setup_pre_commit),
            ("Run tests", lambda: self.run_tests(coverage=True)),
            ("Run linting", self.run_linting),
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if not step_func():
                print(f"❌ Setup failed at: {step_name}")
                return False
        
        print("\n🎉 Development environment setup complete!")
        print("\nNext steps:")
        print("1. Activate virtual environment:")
        if os.name == "nt":
            print(f"   {self.venv_path}\\Scripts\\activate")
        else:
            print(f"   source {self.venv_path}/bin/activate")
        
        print("2. Start developing!")
        print("3. Run 'python scripts/dev_setup.py --help' for more commands")
        
        return True
    
    def run_full_ci_checks(self) -> bool:
        """Run all CI checks locally."""
        print("🔍 Running full CI checks...")
        
        checks = [
            ("Linting", self.run_linting),
            ("Tests", lambda: self.run_tests(coverage=True)),
            ("Security", self.run_security_checks),
            ("Performance", self.run_performance_tests),
            ("Build", self.build_package)
        ]
        
        results = []
        for check_name, check_func in checks:
            print(f"\n📋 Running {check_name} checks...")
            results.append((check_name, check_func()))
        
        print("\n📊 CI Check Results:")
        all_passed = True
        for check_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {check_name}: {status}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n🎉 All CI checks passed!")
            return True
        else:
            print("\n❌ Some CI checks failed")
            return False


def main():
    """Main entry point for development setup script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Mail MCP Development Setup")
    parser.add_argument("--setup", action="store_true",
                       help="Set up development environment")
    parser.add_argument("--test", action="store_true",
                       help="Run test suite")
    parser.add_argument("--lint", action="store_true", 
                       help="Run linting checks")
    parser.add_argument("--format", action="store_true",
                       help="Format code")
    parser.add_argument("--security", action="store_true",
                       help="Run security checks")
    parser.add_argument("--performance", action="store_true",
                       help="Run performance benchmarks")
    parser.add_argument("--build", action="store_true",
                       help="Build package")
    parser.add_argument("--clean", action="store_true",
                       help="Clean build artifacts")
    parser.add_argument("--ci", action="store_true",
                       help="Run all CI checks")
    parser.add_argument("--install-deps", action="store_true",
                       help="Install dependencies")
    
    args = parser.parse_args()
    
    # Determine project root (script is in scripts/ subdirectory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    dev_setup = DevSetup(project_root)
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        parser.print_help()
        return 0
    
    success = True
    
    if args.setup:
        success &= dev_setup.setup_development_environment()
    
    if args.install_deps:
        success &= dev_setup.install_dependencies(dev=True)
    
    if args.format:
        success &= dev_setup.format_code()
    
    if args.lint:
        success &= dev_setup.run_linting()
    
    if args.test:
        success &= dev_setup.run_tests()
    
    if args.security:
        success &= dev_setup.run_security_checks()
    
    if args.performance:
        success &= dev_setup.run_performance_tests()
    
    if args.build:
        success &= dev_setup.build_package()
    
    if args.clean:
        success &= dev_setup.clean_build_artifacts()
    
    if args.ci:
        success &= dev_setup.run_full_ci_checks()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
