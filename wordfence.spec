%global python3_pkgversion 3.11

Name:           python-wordfence
Version:        %{wordfence_version}
Release:        1%{?dist}
Summary:        Wordfence malware and vulnerability scanner command line utility

License:        GPLv3
URL:            https://www.wordfence.com/products/wordfence-cli/
Source0:        https://github.com/wordfence/wordfence-cli/archive/refs/tags/v%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python%{python3_pkgversion}-devel
BuildRequires:  python%{python3_pkgversion}-setuptools
BuildRequires:  pyproject-rpm-macros

%global _description %{expand:
Wordfence CLI is an open source, high performance, multi-process security scanner, written in Python, that quickly scans local and network filesystems to detect PHP malware and WordPress vulnerabilities.}


%description %_description


%package -n python%{python3_pkgversion}-wordfence
Summary:        %{summary}
Requires:       pcre


%description -n python%{python3_pkgversion}-wordfence %_description
# Don't build debuginfo package:
#   https://docs.fedoraproject.org/en-US/packaging-guidelines/Debuginfo/#_missing_debuginfo_packages
%global debug_package %{nil}


# Some build macros require https://src.fedoraproject.org/rpms/pyproject-rpm-macros
%prep
%setup -q -n wordfence-cli
%generate_buildrequires
%pyproject_buildrequires


%build
%pyproject_wheel


%install
%pyproject_install
%pyproject_save_files wordfence


# %check
# %{pytest}


%files -n python%{python3_pkgversion}-wordfence -f %{pyproject_files}
%doc README.md
%license LICENSE
%{_bindir}/wordfence
