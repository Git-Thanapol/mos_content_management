from django import forms
from .models import Employee, TestProduct, Performance, Commission


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["name", "is_graphic", "is_mkt", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "ชื่อพนักงาน"}),
            "is_graphic": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_mkt": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class TestProductForm(forms.ModelForm):
    class Meta:
        model = TestProduct
        fields = [
            "pid", "name", "info", "detail", "image",
            "upload_date", "start_date", "end_date",
            "manual_status", "graphic_members", "mkt_members",
        ]
        widgets = {
            "pid": forms.TextInput(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "info": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "รายละเอียดสินค้าคีย์เวิร์ด..."}),
            "detail": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "หมายเหตุเพิ่มเติม..."}),
            "image": forms.FileInput(attrs={"class": "form-control form-control-sm", "accept": "image/*"}),
            "upload_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "manual_status": forms.Select(attrs={"class": "form-select fw-bold"}),
            "graphic_members": forms.CheckboxSelectMultiple(),
            "mkt_members": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, is_supervisor=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["graphic_members"].queryset = Employee.objects.filter(
            is_graphic=True, is_active=True, user__isnull=False
        )
        self.fields["mkt_members"].queryset = Employee.objects.filter(
            is_mkt=True, is_active=True, user__isnull=False
        )
        # Non-supervisors cannot set locked statuses
        if not is_supervisor:
            self.fields["manual_status"].choices = [
                (TestProduct.STATUS_AUTO, "อัตโนมัติ (ระบบจัดการ)"),
                (TestProduct.STATUS_CANCEL, "ยกเลิก"),
            ]


class PerformanceForm(forms.ModelForm):
    class Meta:
        model = Performance
        fields = ["orders", "sales", "ads", "profit"]
        widgets = {
            "orders": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "sales": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "ads": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "profit": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }


class CommissionForm(forms.ModelForm):
    class Meta:
        model = Commission
        fields = ["total", "status", "note"]
        widgets = {
            "total": forms.NumberInput(attrs={"class": "form-control", "min": "0", "step": "0.01"}),
            "status": forms.Select(attrs={"class": "form-select fw-bold"}),
            "note": forms.TextInput(attrs={"class": "form-control", "placeholder": "หมายเหตุ"}),
        }


class DateRangeForm(forms.Form):
    DATE_FIELD_CHOICES = [
        ("upload_date", "วันที่ลงข้อมูล"),
        ("start_date", "วันที่ทดสอบ"),
    ]
    date_field = forms.ChoiceField(
        choices=DATE_FIELD_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
        label="กรองตามวันที่",
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control form-control-sm", "type": "date"}),
        label="ตั้งแต่วันที่",
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control form-control-sm", "type": "date"}),
        label="ถึงวันที่",
    )
