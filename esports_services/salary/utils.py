class TotalDataMixin:
    def get_total_values(self, workshifts):
        summary_bar_revenue = 0.0
        summary_game_zone_revenue = 0.0
        summary_vr_revenue = 0.0
        total_revenue = 0.0
        total_salary = 0.0
        summary_error = 0.0
        summary_shortage = 0.0

        for get_shift in workshifts:
            summary_bar_revenue += get_shift.bar_revenue
            summary_game_zone_revenue += get_shift.game_zone_revenue
            summary_vr_revenue += get_shift.vr_revenue
            total_revenue += get_shift.get_summary_revenue()
            summary_error += get_shift.game_zone_error
            if not get_shift.shortage_paid:
                summary_shortage += get_shift.shortage
            if get_shift.is_verified:
                total_salary += get_shift.kpi_salary_calculate(self.request.user)['shift_salary']

        quantity_shifts = len(workshifts)
        if len(workshifts):
            average_revenue = round(total_revenue / quantity_shifts)
        else:
            average_revenue = 0.0

        returned_dict = {
            'bar': summary_bar_revenue,
            'game_zone': summary_game_zone_revenue,
            'game_zone_error': summary_error,
            'vr': summary_vr_revenue,
            'sum_revenue': total_revenue,
            'quantity_shifts': quantity_shifts,
            'average_revenue': average_revenue,
            'summary_shortage': summary_shortage,
            'total_salary': total_salary,
        }
        return returned_dict