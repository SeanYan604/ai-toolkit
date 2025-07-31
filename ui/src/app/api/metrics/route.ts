import { NextResponse } from 'next/server';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const jobId = searchParams.get('jobId');
  const metricType = searchParams.get('type') || 'loss';
  const limit = parseInt(searchParams.get('limit') || '1000');
  const stepStart = parseInt(searchParams.get('stepStart') || '0');
  const stepEnd = searchParams.get('stepEnd') ? parseInt(searchParams.get('stepEnd')!) : undefined;

  if (!jobId) {
    return NextResponse.json({ error: 'jobId is required' }, { status: 400 });
  }

  try {
    // 构建查询条件
    const whereCondition: any = {
      job_id: jobId,
      metric_type: metricType,
      step: { gte: stepStart }
    };

    if (stepEnd !== undefined) {
      whereCondition.step.lte = stepEnd;
    }

    const metrics = await prisma.trainingMetrics.findMany({
      where: whereCondition,
      orderBy: { step: 'asc' },
      take: limit
    });

    // 数据格式化为图表友好格式
    const chartData = formatMetricsForChart(metrics);
    
    // 获取可用的metric名称
    const availableMetrics = await getAvailableMetrics(jobId, metricType);

    return NextResponse.json({
      success: true,
      data: chartData,
      totalSteps: metrics.length,
      availableMetrics: availableMetrics,
      jobId: jobId,
      metricType: metricType
    });
  } catch (error) {
    console.error('Error fetching metrics:', error);
    return NextResponse.json({ error: 'Failed to fetch metrics' }, { status: 500 });
  }
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const jobId = searchParams.get('jobId');
  const olderThanDays = searchParams.get('olderThanDays');
  const clearAll = searchParams.get('clearAll') === 'true';

  if (!jobId) {
    return NextResponse.json({ error: 'jobId is required' }, { status: 400 });
  }

  try {
    let deletedCount;

    if (clearAll) {
      // 删除指定job的所有metrics数据
      deletedCount = await prisma.trainingMetrics.deleteMany({
        where: {
          job_id: jobId
        }
      });
      
      return NextResponse.json({
        success: true,
        deletedCount: deletedCount.count,
        message: `Deleted all ${deletedCount.count} metrics for job "${jobId}"`
      });
    } else {
      // 删除指定天数之前的数据（原有功能保持）
      const days = parseInt(olderThanDays || '30');
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - days);

      deletedCount = await prisma.trainingMetrics.deleteMany({
        where: {
          job_id: jobId,
          timestamp: {
            lt: cutoffDate
          }
        }
      });

      return NextResponse.json({
        success: true,
        deletedCount: deletedCount.count,
        message: `Deleted ${deletedCount.count} metrics older than ${days} days`
      });
    }
  } catch (error) {
    console.error('Error deleting metrics:', error);
    return NextResponse.json({ error: 'Failed to delete metrics' }, { status: 500 });
  }
}

/**
 * 将数据库查询结果格式化为图表友好的格式
 */
function formatMetricsForChart(metrics: Array<{
  step: number;
  timestamp: Date | string;
  metric_name: string;
  value: number;
}>) {
  const groupedByStep = metrics.reduce((acc: any, metric: any) => {
    if (!acc[metric.step]) {
      acc[metric.step] = { 
        step: metric.step, 
        timestamp: typeof metric.timestamp === 'string' ? metric.timestamp : metric.timestamp.toISOString()
      };
    }
    acc[metric.step][metric.metric_name] = metric.value;
    return acc;
  }, {});

  return Object.values(groupedByStep);
}

/**
 * 获取指定job和metric类型的所有可用metric名称
 */
async function getAvailableMetrics(jobId: string, metricType: string) {
  try {
    const result = await prisma.trainingMetrics.findMany({
      where: {
        job_id: jobId,
        metric_type: metricType
      },
      select: {
        metric_name: true
      },
      distinct: ['metric_name']
    });

    return result.map((item: any) => item.metric_name);
  } catch (error) {
    console.error('Error fetching available metrics:', error);
    return [];
  }
}