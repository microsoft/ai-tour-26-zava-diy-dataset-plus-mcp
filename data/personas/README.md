# Zava Organization Personas

This folder contains the complete organizational chart data for Zava, including employee personas and their corresponding profile pictures. The data was automatically extracted from the Zava Org Chart PowerPoint presentation using a combination of AI generated Python code and VS Code Copilot.

## Contents

- **`personas.yaml`** - Complete structured data of all Zava employees including names, roles, departments, and photo references
- **`images/`** - Directory containing all employee profile pictures extracted from the presentation
- **`org-chart.png`** - Original organizational chart image from the PowerPoint presentation

## Data Structure

The `personas.yaml` file contains a structured list of all employees with the following fields:
- `name` - Full name of the employee
- `role` - Job title/position
- `photo_name` - Filename of the corresponding profile picture
- `department` - Department/division the employee belongs to

## Example Personas

Here are a few examples from the organizational data:

```yaml
personas:
- name: Kayo Miwa
  role: CEO
  photo_name: kayo-miwa.png
  department: leadership

- name: Carlos Slattery
  role: Chief Technical Officer
  photo_name: carlos-slattery.png
  department: technology

- name: Elvia Atkins
  role: App Developer
  photo_name: elvia-atkins.png
  department: technology
```

## Departments

The organization is structured into the following departments:
- `leadership` - Executive leadership
- `technology` - Technology and development teams
- `security` - Information security and compliance
- `financial` - Finance and procurement
- `product_dev` - Product development and R&D
- `marketing` - Marketing and market research
- `contact_center` - Customer service
- `sales_enablement` - Sales support
- `factory_ops` - Manufacturing and operations
- `executive` - C-level executives
