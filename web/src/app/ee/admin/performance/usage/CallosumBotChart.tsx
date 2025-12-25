import { ThreeDotsLoader } from "@/components/Loading";
import { getDatesList, useCallosumBotAnalytics } from "../lib";
import { DateRangePickerValue } from "@/components/dateRangeSelectors/AdminDateRangeSelector";
import Text from "@/components/ui/text";
import Title from "@/components/ui/title";
import CardSection from "@/components/admin/CardSection";
import { AreaChartDisplay } from "@/components/ui/areaChart";

export function CallosumBotChart({
  timeRange,
}: {
  timeRange: DateRangePickerValue;
}) {
  const {
    data: callosumBotAnalyticsData,
    isLoading: isCallosumBotAnalyticsLoading,
    error: callosumBotAnalyticsError,
  } = useCallosumBotAnalytics(timeRange);

  let chart;
  if (isCallosumBotAnalyticsLoading) {
    chart = (
      <div className="h-80 flex flex-col">
        <ThreeDotsLoader />
      </div>
    );
  } else if (
    !callosumBotAnalyticsData ||
    callosumBotAnalyticsData[0] == undefined ||
    callosumBotAnalyticsError
  ) {
    chart = (
      <div className="h-80 text-red-600 text-bold flex flex-col">
        <p className="m-auto">Failed to fetch feedback data...</p>
      </div>
    );
  } else {
    const initialDate =
      timeRange.from || new Date(callosumBotAnalyticsData[0].date);
    const dateRange = getDatesList(initialDate);

    const dateToCallosumBotAnalytics = new Map(
      callosumBotAnalyticsData.map((callosumBotAnalyticsEntry) => [
        callosumBotAnalyticsEntry.date,
        callosumBotAnalyticsEntry,
      ])
    );

    chart = (
      <AreaChartDisplay
        className="mt-4"
        data={dateRange.map((dateStr) => {
          const callosumBotAnalyticsForDate = dateToCallosumBotAnalytics.get(dateStr);
          return {
            Day: dateStr,
            "Total Queries": callosumBotAnalyticsForDate?.total_queries || 0,
            "Automatically Resolved":
              callosumBotAnalyticsForDate?.auto_resolved || 0,
          };
        })}
        categories={["Total Queries", "Automatically Resolved"]}
        index="Day"
        colors={["indigo", "fuchsia"]}
        yAxisWidth={60}
      />
    );
  }

  return (
    <CardSection className="mt-8">
      <Title>Slack Channel</Title>
      <Text>Total Queries vs Auto Resolved</Text>
      {chart}
    </CardSection>
  );
}
