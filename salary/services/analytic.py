import datetime

from dateutil.relativedelta import relativedelta

from django.db.models import Sum, Avg

class MonthlyAnaliticData:
    def get_fields_dict(self) -> dict:
        fields = (
            'summary_revenue', 'bar_revenue', 'game_zone_subtotal',
            'game_zone_error', 'additional_services_revenue', 'hookah_revenue',
            'shortage', 'summary_revenue__avg',
        )
        self.current_month_queryset = self.object_list.filter(
            shift_date__month=self.month,
            shift_date__year=self.year,
        )

        # if not self.current_month_queryset:
        #     raise Http404

        self.current_date = datetime.date(self.year, self.month, 1)

        self.previous_month_date = self.current_date - relativedelta(months=1)
        self.previous_month_queryset = self.object_list.filter(
            shift_date__month=self.previous_month_date.month,
            shift_date__year=self.previous_month_date.year,
        )

        values_dict = dict()
        operations_list = [
            Sum(field) if '__avg' not in field
            else Avg(field.split('__')[0])
            for field in fields
        ]

        current_month_values = self.current_month_queryset.aggregate(*operations_list)
        previous_month_values = self.previous_month_queryset.aggregate(*operations_list)

        for field in current_month_values.keys():
            current_month_value = round(current_month_values.get(field, 0), 2)
            previous_month_value = round(
                previous_month_values.get(field, 0), 2
            ) if previous_month_values.get(field, 0) else 0

            if current_month_value == 0.0:
                ratio = 100.0
            elif current_month_value > previous_month_value:
                ratio = round((current_month_value - previous_month_value) /
                            current_month_value * 100, 2)
            elif current_month_value < previous_month_value:
                ratio = round((previous_month_value - current_month_value) /
                            previous_month_value * 100, 2)

            values_dict[field] = (
                        previous_month_value,
                        current_month_value,
                        ratio,
                    )

        return values_dict

    def get_linechart_data(self) -> list:
        """Return list of lists with revenue data for Google LineChart

        Returns:
            list: list of lists [day_of_month, previous_month_revenue, current_month_revenue]
        """
        current_month_list =  self.current_month_queryset.values_list(
            'shift_date__day',
            'summary_revenue')
        previous_month_list = self.previous_month_queryset.values_list(
            'shift_date__day',
            'summary_revenue')
        linechart_data_list = list()
        for first_element in previous_month_list:
            for second_element in current_month_list:
                if first_element[0] == second_element[0]:
                    data_row = list(first_element)
                    data_row.append(second_element[1])
                    linechart_data_list.append(data_row)

        return linechart_data_list

    def get_piechart_data(self, analytic_data: dict) -> list:
        categories = {
            'bar_revenue': 'Бар',
            'game_zone_subtotal': 'Game zone',
            'additional_services_revenue': 'Доп. услуги',
            'hookah_revenue': 'Кальян',
        }

        piechart_data = list()

        for category in categories.keys():
            piechart_data.append(
                [categories.get(category), analytic_data.get(f'{category}__sum')[1]]
            )

        return piechart_data