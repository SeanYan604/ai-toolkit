import { NextResponse } from 'next/server';
import { getTrainingFolder } from '@/server/settings';
import * as fs from 'fs';
import * as path from 'path';
import yaml from 'yaml';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const jobName = searchParams.get('jobName');

  if (!jobName) {
    return NextResponse.json({ error: 'jobName is required' }, { status: 400 });
  }

  try {
    const trainingFolder = await getTrainingFolder();
    const configPath = path.join(trainingFolder, jobName, 'dynamic_config.yaml');

    if (!fs.existsSync(configPath)) {
      // 返回默认配置
      return NextResponse.json({
        success: true,
        config: {
          sample_every: 100,
          save_every: null,
          log_every: null,
          last_updated: null
        },
        configExists: false,
        configPath: configPath
      });
    }

    const configContent = fs.readFileSync(configPath, 'utf8');
    const config = yaml.parse(configContent) || {};

    return NextResponse.json({
      success: true,
      config: config,
      configExists: true,
      configPath: configPath
    });
  } catch (error) {
    console.error('Error reading dynamic config:', error);
    return NextResponse.json({ 
      error: 'Failed to read dynamic config',
      details: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { jobName, config } = body;

    if (!jobName) {
      return NextResponse.json({ error: 'jobName is required' }, { status: 400 });
    }

    if (!config) {
      return NextResponse.json({ error: 'config is required' }, { status: 400 });
    }

    // 验证配置字段
    const validatedConfig: any = {};
    
    if (config.sample_every !== undefined) {
      const sampleEvery = parseInt(config.sample_every);
      if (isNaN(sampleEvery) || sampleEvery <= 0) {
        return NextResponse.json({ error: 'sample_every must be a positive integer' }, { status: 400 });
      }
      validatedConfig.sample_every = sampleEvery;
    }

    if (config.save_every !== undefined && config.save_every !== null) {
      const saveEvery = parseInt(config.save_every);
      if (isNaN(saveEvery) || saveEvery <= 0) {
        return NextResponse.json({ error: 'save_every must be a positive integer or null' }, { status: 400 });
      }
      validatedConfig.save_every = saveEvery;
    } else if (config.save_every === null) {
      validatedConfig.save_every = null;
    }

    if (config.log_every !== undefined && config.log_every !== null) {
      const logEvery = parseInt(config.log_every);
      if (isNaN(logEvery) || logEvery <= 0) {
        return NextResponse.json({ error: 'log_every must be a positive integer or null' }, { status: 400 });
      }
      validatedConfig.log_every = logEvery;
    } else if (config.log_every === null) {
      validatedConfig.log_every = null;
    }

    // 添加更新时间戳
    validatedConfig.last_updated = Date.now() / 1000;

    const trainingFolder = await getTrainingFolder();
    const jobFolder = path.join(trainingFolder, jobName);
    const configPath = path.join(jobFolder, 'dynamic_config.yaml');

    // 确保目录存在
    if (!fs.existsSync(jobFolder)) {
      fs.mkdirSync(jobFolder, { recursive: true });
    }

    // 如果文件已存在，先读取现有配置，然后合并
    let existingConfig = {};
    if (fs.existsSync(configPath)) {
      try {
        const existingContent = fs.readFileSync(configPath, 'utf8');
        existingConfig = yaml.parse(existingContent) || {};
      } catch (error) {
        console.warn('Failed to parse existing config, creating new one:', error);
      }
    }

    // 合并配置
    const finalConfig = { ...existingConfig, ...validatedConfig };

    // 写入配置文件
    const yamlContent = yaml.stringify(finalConfig, { indent: 2 });
    fs.writeFileSync(configPath, yamlContent, 'utf8');

    return NextResponse.json({
      success: true,
      config: finalConfig,
      configPath: configPath,
      message: 'Dynamic config updated successfully'
    });
  } catch (error) {
    console.error('Error updating dynamic config:', error);
    return NextResponse.json({ 
      error: 'Failed to update dynamic config',
      details: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}