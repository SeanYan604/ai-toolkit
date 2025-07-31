import { NextResponse } from 'next/server';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const jobId = searchParams.get('jobId');
  const metricType = searchParams.get('type') || 'loss';
  const lastStep = parseInt(searchParams.get('lastStep') || '0');

  if (!jobId) {
    return NextResponse.json({ error: 'jobId is required' }, { status: 400 });
  }

  // 创建 Server-Sent Events 流
  const encoder = new TextEncoder();
  let closed = false;

  const stream = new ReadableStream({
    start(controller) {
      // 立即发送一次数据
      sendLatestData();

      // 每5秒检查并发送新数据
      const interval = setInterval(async () => {
        if (closed) {
          clearInterval(interval);
          return;
        }
        await sendLatestData();
      }, 5000);

      async function sendLatestData() {
        try {
          const latestMetrics = await getLatestMetrics(jobId, metricType, lastStep);
          
          if (latestMetrics.length > 0) {
            const data = JSON.stringify({
              type: 'metrics_update',
              data: latestMetrics,
              timestamp: new Date().toISOString()
            });
            
            const eventData = `data: ${data}\n\n`;
            controller.enqueue(encoder.encode(eventData));
          } else {
            // 发送心跳包
            const heartbeat = `data: ${JSON.stringify({ type: 'heartbeat', timestamp: new Date().toISOString() })}\n\n`;
            controller.enqueue(encoder.encode(heartbeat));
          }
        } catch (error) {
          console.error('Stream error:', error);
          const errorData = `data: ${JSON.stringify({ type: 'error', message: 'Failed to fetch metrics' })}\n\n`;
          controller.enqueue(encoder.encode(errorData));
        }
      }

      // 清理函数
      return () => {
        closed = true;
        clearInterval(interval);
      };
    },
    
    cancel() {
      closed = true;
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Cache-Control'
    },
  });
}

/**
 * 获取最新的metrics数据
 */
async function getLatestMetrics(jobId: string, metricType: string, lastStep: number) {
  try {
    const metrics = await prisma.trainingMetrics.findMany({
      where: {
        job_id: jobId,
        metric_type: metricType,
        step: {
          gt: lastStep
        }
      },
      orderBy: { step: 'asc' },
      take: 100 // 限制每次返回的数据量
    });

    // 格式化数据
    const groupedByStep = metrics.reduce((acc: any, metric: any) => {
      if (!acc[metric.step]) {
        acc[metric.step] = { 
          step: metric.step, 
          timestamp: metric.timestamp 
        };
      }
      acc[metric.step][metric.metric_name] = metric.value;
      return acc;
    }, {});

    return Object.values(groupedByStep);
  } catch (error) {
    console.error('Error fetching latest metrics:', error);
    return [];
  }
}