import os
import sys
import django
import random
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from faker import Faker

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_queue.settings')
django.setup()

from navigation.models import (
    Patient, Department, Equipment, Examination
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化Faker
fake = Faker(['zh_CN'])

def generate_departments():
    """生成科室数据"""
    departments = [
        {
            'name': '放射科',
            'code': 'RAD',
            'description': '提供X光、CT、MRI等影像检查服务',
            'location': '门诊楼2层',
            'floor': '2',
            'building': '门诊楼',
            'contact_phone': '0123-4567890',
            'operating_hours': '08:00-17:00',
            'max_daily_patients': 50,
            'average_service_time': 20
        },
        {
            'name': '超声科',
            'code': 'US',
            'description': '提供各类超声检查服务',
            'location': '门诊楼3层',
            'floor': '3',
            'building': '门诊楼',
            'contact_phone': '0123-4567891',
            'operating_hours': '08:00-17:00',
            'max_daily_patients': 30,
            'average_service_time': 15
        },
        {
            'name': '心电图室',
            'code': 'ECG',
            'description': '提供心电图、动态心电图等检查服务',
            'location': '门诊楼2层',
            'floor': '2',
            'building': '门诊楼',
            'contact_phone': '0123-4567892',
            'operating_hours': '08:00-17:00',
            'max_daily_patients': 40,
            'average_service_time': 10
        },
        {
            'name': '核医学科',
            'code': 'NM',
            'description': '提供核素扫描、PET-CT等核医学检查服务',
            'location': '医技楼1层',
            'floor': '1',
            'building': '医技楼',
            'contact_phone': '0123-4567893',
            'operating_hours': '08:00-16:00',
            'max_daily_patients': 20,
            'average_service_time': 40
        },
        {
            'name': '内镜中心',
            'code': 'END',
            'description': '提供胃镜、肠镜等内窥镜检查服务',
            'location': '医技楼3层',
            'floor': '3',
            'building': '医技楼',
            'contact_phone': '0123-4567894',
            'operating_hours': '08:00-16:00',
            'max_daily_patients': 30,
            'average_service_time': 25
        },
        {
            'name': '检验科',
            'code': 'LAB',
            'description': '提供血液、尿液、生化等各类医学检验服务',
            'location': '医技楼2层',
            'floor': '2',
            'building': '医技楼',
            'contact_phone': '0123-4567895',
            'operating_hours': '07:30-17:00',
            'max_daily_patients': 200,
            'average_service_time': 5
        },
        {
            'name': '病理科',
            'code': 'PATH',
            'description': '提供各类组织病理学检查服务',
            'location': '医技楼4层',
            'floor': '4',
            'building': '医技楼',
            'contact_phone': '0123-4567896',
            'operating_hours': '08:00-16:00',
            'max_daily_patients': 30,
            'average_service_time': 15
        },
        {
            'name': '功能检查科',
            'code': 'FUNC',
            'description': '提供肺功能、脑电图等功能检查服务',
            'location': '门诊楼4层',
            'floor': '4',
            'building': '门诊楼',
            'contact_phone': '0123-4567897',
            'operating_hours': '08:00-17:00',
            'max_daily_patients': 40,
            'average_service_time': 20
        }
    ]
    
    created_departments = []
    for dept_data in departments:
        try:
            dept, created = Department.objects.get_or_create(
                code=dept_data['code'],
                defaults=dept_data
            )
            if created:
                logger.info(f"创建科室: {dept.name}")
            else:
                logger.info(f"科室已存在: {dept.name}")
            created_departments.append(dept)
        except Exception as e:
            logger.error(f"创建科室 {dept_data['name']} 时出错: {str(e)}")
    
    return created_departments

def generate_equipment(departments):
    """生成设备数据"""
    equipment_data = {
        'RAD': [
            {
                'name': 'DR机',
                'code': 'DR001',
                'model': 'GE-DR-2000',
                'manufacturer': 'GE Healthcare',
                'average_service_time': 10,
                'description': 'DR数字化X射线摄影系统',
                'maintenance_period': 30
            },
            {
                'name': 'CT机',
                'code': 'CT001',
                'model': 'Siemens SOMATOM',
                'manufacturer': 'Siemens Healthineers',
                'average_service_time': 20,
                'description': '64排螺旋CT',
                'maintenance_period': 30
            },
            {
                'name': 'MRI机',
                'code': 'MRI001',
                'model': 'Philips Ingenia 3.0T',
                'manufacturer': 'Philips Healthcare',
                'average_service_time': 30,
                'description': '3.0T磁共振成像系统',
                'maintenance_period': 30
            },
            {
                'name': 'DR机2号',
                'code': 'DR002',
                'model': 'Siemens Ysio Max',
                'manufacturer': 'Siemens Healthineers',
                'average_service_time': 10,
                'description': '数字化X射线摄影系统',
                'maintenance_period': 30
            },
            {
                'name': 'CT机2号',
                'code': 'CT002',
                'model': 'Canon Aquilion ONE',
                'manufacturer': 'Canon Medical',
                'average_service_time': 20,
                'description': '320排面源探测器CT',
                'maintenance_period': 30
            },
            {
                'name': 'MRI机2号',
                'code': 'MRI002',
                'model': 'Siemens MAGNETOM Vida',
                'manufacturer': 'Siemens Healthineers',
                'average_service_time': 30,
                'description': '3.0T磁共振成像系统',
                'maintenance_period': 30
            }
        ],
        'US': [
            {
                'name': '彩超机1号',
                'code': 'US001',
                'model': 'GE Voluson E10',
                'manufacturer': 'GE Healthcare',
                'average_service_time': 15,
                'description': '高端彩色超声诊断系统',
                'maintenance_period': 30
            },
            {
                'name': '彩超机2号',
                'code': 'US002',
                'model': 'Philips EPIQ Elite',
                'manufacturer': 'Philips Healthcare',
                'average_service_time': 15,
                'description': '高端彩色超声诊断系统',
                'maintenance_period': 30
            },
            {
                'name': '彩超机3号',
                'code': 'US003',
                'model': 'Canon Aplio i800',
                'manufacturer': 'Canon Medical',
                'average_service_time': 15,
                'description': '高端彩色超声诊断系统',
                'maintenance_period': 30
            },
            {
                'name': '便携式超声机',
                'code': 'US004',
                'model': 'Mindray M9',
                'manufacturer': 'Mindray',
                'average_service_time': 15,
                'description': '便携式彩色超声诊断系统',
                'maintenance_period': 30
            }
        ],
        'ECG': [
            {
                'name': '心电图机1号',
                'code': 'ECG001',
                'model': 'GE MAC 2000',
                'manufacturer': 'GE Healthcare',
                'average_service_time': 10,
                'description': '12导联心电图机',
                'maintenance_period': 30
            },
            {
                'name': '动态心电图记录仪',
                'code': 'ECG002',
                'model': 'Holter-3000',
                'manufacturer': 'Mindray',
                'average_service_time': 20,
                'description': '24小时动态心电图记录系统',
                'maintenance_period': 30
            },
            {
                'name': '心电图机2号',
                'code': 'ECG003',
                'model': 'Philips PageWriter TC70',
                'manufacturer': 'Philips Healthcare',
                'average_service_time': 10,
                'description': '12导联心电图机',
                'maintenance_period': 30
            },
            {
                'name': '运动心电图系统',
                'code': 'ECG004',
                'model': 'GE CASE',
                'manufacturer': 'GE Healthcare',
                'average_service_time': 45,
                'description': '运动负荷心电图系统',
                'maintenance_period': 30
            }
        ],
        'NM': [
            {
                'name': 'PET-CT机',
                'code': 'PET001',
                'model': 'GE Discovery MI',
                'manufacturer': 'GE Healthcare',
                'average_service_time': 40,
                'description': 'PET-CT显像系统',
                'maintenance_period': 30
            },
            {
                'name': 'SPECT机',
                'code': 'SPECT001',
                'model': 'Siemens Symbia',
                'manufacturer': 'Siemens Healthineers',
                'average_service_time': 30,
                'description': '单光子发射计算机断层显像系统',
                'maintenance_period': 30
            },
            {
                'name': 'PET-MR机',
                'code': 'PET002',
                'model': 'Siemens Biograph mMR',
                'manufacturer': 'Siemens Healthineers',
                'average_service_time': 60,
                'description': 'PET-MR融合显像系统',
                'maintenance_period': 30
            }
        ],
        'END': [
            {
                'name': '电子胃镜',
                'code': 'GAS001',
                'model': 'Olympus GIF-H290',
                'manufacturer': 'Olympus',
                'average_service_time': 20,
                'description': '高清电子胃镜系统',
                'maintenance_period': 15
            },
            {
                'name': '电子肠镜',
                'code': 'COL001',
                'model': 'Olympus CF-H290',
                'manufacturer': 'Olympus',
                'average_service_time': 30,
                'description': '高清电子结肠镜系统',
                'maintenance_period': 15
            },
            {
                'name': '支气管镜',
                'code': 'BRON001',
                'model': 'Olympus BF-H290',
                'manufacturer': 'Olympus',
                'average_service_time': 30,
                'description': '电子支气管镜系统',
                'maintenance_period': 15
            },
            {
                'name': '胶囊内镜',
                'code': 'CAP001',
                'model': 'Given PillCam',
                'manufacturer': 'Medtronic',
                'average_service_time': 20,
                'description': '胶囊内镜系统',
                'maintenance_period': 30
            }
        ],
        'LAB': [
            {
                'name': '全自动生化分析仪',
                'code': 'BIO001',
                'model': 'Roche Cobas 8000',
                'manufacturer': 'Roche',
                'average_service_time': 5,
                'description': '全自动生化分析系统',
                'maintenance_period': 30
            },
            {
                'name': '全自动血液分析仪',
                'code': 'HEM001',
                'model': 'Sysmex XN-3000',
                'manufacturer': 'Sysmex',
                'average_service_time': 5,
                'description': '全自动血液分析系统',
                'maintenance_period': 30
            },
            {
                'name': '全自动免疫分析仪',
                'code': 'IMM001',
                'model': 'Abbott Architect i2000',
                'manufacturer': 'Abbott',
                'average_service_time': 10,
                'description': '全自动免疫分析系统',
                'maintenance_period': 30
            },
            {
                'name': '全自动凝血分析仪',
                'code': 'COAG001',
                'model': 'Sysmex CS-5100',
                'manufacturer': 'Sysmex',
                'average_service_time': 10,
                'description': '全自动凝血分析系统',
                'maintenance_period': 30
            },
            {
                'name': '全自动尿液分析仪',
                'code': 'UA001',
                'model': 'Sysmex UN-2000',
                'manufacturer': 'Sysmex',
                'average_service_time': 5,
                'description': '全自动尿液分析系统',
                'maintenance_period': 30
            }
        ],
        'PATH': [
            {
                'name': '自动染色机',
                'code': 'STAIN001',
                'model': 'Roche BenchMark',
                'manufacturer': 'Roche',
                'average_service_time': 15,
                'description': '全自动免疫组化染色系统',
                'maintenance_period': 30
            },
            {
                'name': '数字切片扫描仪',
                'code': 'SCAN001',
                'model': 'Leica Aperio AT2',
                'manufacturer': 'Leica',
                'average_service_time': 10,
                'description': '数字病理切片扫描系统',
                'maintenance_period': 30
            },
            {
                'name': '切片机',
                'code': 'SECT001',
                'model': 'Leica RM2255',
                'manufacturer': 'Leica',
                'average_service_time': 10,
                'description': '全自动切片机',
                'maintenance_period': 30
            },
            {
                'name': '组织脱水机',
                'code': 'PROC001',
                'model': 'Leica ASP6025',
                'manufacturer': 'Leica',
                'average_service_time': 20,
                'description': '全自动组织脱水机',
                'maintenance_period': 30
            },
            {
                'name': '免疫组化染色机',
                'code': 'IHC001',
                'model': 'Ventana BenchMark GX',
                'manufacturer': 'Roche',
                'average_service_time': 15,
                'description': '全自动免疫组化染色系统',
                'maintenance_period': 30
            }
        ],
        'FUNC': [
            {
                'name': '肺功能仪',
                'code': 'PFT001',
                'model': 'Jaeger MasterScreen',
                'manufacturer': 'CareFusion',
                'average_service_time': 20,
                'description': '肺功能检测系统',
                'maintenance_period': 30
            },
            {
                'name': '脑电图仪',
                'code': 'EEG001',
                'model': 'Nihon Kohden EEG-1200',
                'manufacturer': 'Nihon Kohden',
                'average_service_time': 30,
                'description': '数字脑电图系统',
                'maintenance_period': 30
            },
            {
                'name': '动态脑电图记录仪',
                'code': 'AEEG001',
                'model': 'Nihon Kohden JE-921A',
                'manufacturer': 'Nihon Kohden',
                'average_service_time': 40,
                'description': '动态脑电图记录系统',
                'maintenance_period': 30
            },
            {
                'name': '诱发电位仪',
                'code': 'EP001',
                'model': 'Nicolet EDX',
                'manufacturer': 'Natus',
                'average_service_time': 30,
                'description': '诱发电位检查系统',
                'maintenance_period': 30
            },
            {
                'name': '经颅多普勒',
                'code': 'TCD001',
                'model': 'DWL Multi-Dop X',
                'manufacturer': 'Compumedics',
                'average_service_time': 25,
                'description': '经颅多普勒超声系统',
                'maintenance_period': 30
            }
        ]
    }
    
    created_equipment = []
    for dept in departments:
        dept_equipment = equipment_data.get(dept.code, [])
        for equip_data in dept_equipment:
            try:
                equip_data['department'] = dept
                equip_data['location'] = dept.location
                equip_data['status'] = 'available'
                
                equip, created = Equipment.objects.get_or_create(
                    code=equip_data['code'],
                    defaults=equip_data
                )
                if created:
                    logger.info(f"创建设备: {equip.name}")
                else:
                    logger.info(f"设备已存在: {equip.name}")
                created_equipment.append(equip)
            except Exception as e:
                logger.error(f"创建设备 {equip_data['name']} 时出错: {str(e)}")
    
    return created_equipment

def generate_examinations(departments, equipment):
    """生成检查项目数据"""
    examination_data = {
        'RAD': [
            {
                'name': '胸部X光检查',
                'code': 'CXR',
                'duration': 10,
                'price': 80.0,
                'description': '胸部X光检查，可检查肺部、心脏等情况',
                'preparation': '无特殊准备',
                'contraindications': '孕妇禁忌'
            },
            {
                'name': '头颅CT检查',
                'code': 'HCT',
                'duration': 20,
                'price': 200.0,
                'description': '头颅CT检查，可检查颅内情况',
                'preparation': '检查前4小时禁食',
                'contraindications': '孕妇禁忌'
            },
            {
                'name': '腰椎MRI检查',
                'code': 'LMRI',
                'duration': 30,
                'price': 800.0,
                'description': '腰椎核磁共振检查',
                'preparation': '检查前禁食4小时，去除金属物品',
                'contraindications': '体内有金属物品者禁忌'
            },
            {
                'name': '全脊柱X光检查',
                'code': 'SXR',
                'duration': 15,
                'price': 120.0,
                'description': '全脊柱X光检查，包括颈椎、胸椎、腰椎正侧位片',
                'preparation': '无特殊准备',
                'contraindications': '孕妇禁忌'
            },
            {
                'name': '腹部CT检查',
                'code': 'ACT',
                'duration': 20,
                'price': 350.0,
                'description': '腹部CT检查，可检查腹部器官情况',
                'preparation': '检查前4小时禁食',
                'contraindications': '孕妇禁忌'
            },
            {
                'name': '头颅MRI检查',
                'code': 'HMRI',
                'duration': 30,
                'price': 900.0,
                'description': '头颅核磁共振检查',
                'preparation': '检查前去除金属物品',
                'contraindications': '体内有金属物品者禁忌'
            }
        ],
        'US': [
            {
                'name': '腹部超声检查',
                'code': 'AUS',
                'duration': 15,
                'price': 120.0,
                'description': '腹部超声检查，可检查肝胆脾胰等器官',
                'preparation': '检查前禁食8小时',
                'contraindications': ''
            },
            {
                'name': '心脏超声检查',
                'code': 'ECHO',
                'duration': 20,
                'price': 180.0,
                'description': '心脏超声检查，可检查心脏结构和功能',
                'preparation': '无特殊准备',
                'contraindications': ''
            },
            {
                'name': '甲状腺超声检查',
                'code': 'TUS',
                'duration': 15,
                'price': 120.0,
                'description': '甲状腺超声检查',
                'preparation': '无特殊准备',
                'contraindications': ''
            },
            {
                'name': '乳腺超声检查',
                'code': 'BUS',
                'duration': 20,
                'price': 150.0,
                'description': '乳腺超声检查',
                'preparation': '无特殊准备',
                'contraindications': ''
            }
        ],
        'ECG': [
            {
                'name': '常规心电图检查',
                'code': 'ECG',
                'duration': 10,
                'price': 35.0,
                'description': '12导联心电图检查',
                'preparation': '检查前休息5分钟',
                'contraindications': ''
            },
            {
                'name': '24小时动态心电图',
                'code': 'HECG',
                'duration': 20,
                'price': 200.0,
                'description': '24小时动态心电图记录',
                'preparation': '穿着舒适衣物，保持正常生活作息',
                'contraindications': ''
            },
            {
                'name': '运动负荷心电图',
                'code': 'EECG',
                'duration': 45,
                'price': 280.0,
                'description': '运动负荷心电图检查',
                'preparation': '穿运动服装，空腹2小时',
                'contraindications': '急性心肌梗死患者禁忌'
            }
        ],
        'NM': [
            {
                'name': '全身PET-CT检查',
                'code': 'PET',
                'duration': 40,
                'price': 8000.0,
                'description': '全身PET-CT显像检查，用于肿瘤的诊断和分期',
                'preparation': '检查前禁食6小时，注射显像剂后需要等待约1小时',
                'contraindications': '孕妇禁忌'
            },
            {
                'name': '骨显像检查',
                'code': 'BONE',
                'duration': 30,
                'price': 1200.0,
                'description': '骨骼核素显像检查，用于骨转移等的诊断',
                'preparation': '检查前无特殊准备，注射显像剂后需要等待2-3小时',
                'contraindications': '孕妇禁忌'
            },
            {
                'name': '甲状腺显像',
                'code': 'TSC',
                'duration': 30,
                'price': 800.0,
                'description': '甲状腺核素显像检查',
                'preparation': '检查前禁食4小时',
                'contraindications': '孕妇禁忌'
            }
        ],
        'END': [
            {
                'name': '胃镜检查',
                'code': 'GAS',
                'duration': 20,
                'price': 350.0,
                'description': '胃镜检查，可观察食管、胃、十二指肠病变',
                'preparation': '检查前禁食8小时，禁水4小时',
                'contraindications': '消化道大出血患者禁忌'
            },
            {
                'name': '肠镜检查',
                'code': 'COL',
                'duration': 30,
                'price': 450.0,
                'description': '结肠镜检查，可观察全结肠及末端回肠病变',
                'preparation': '检查前需要完整肠道准备，包括限制饮食和服用泻药',
                'contraindications': '肠道穿孔患者禁忌'
            },
            {
                'name': '支气管镜检查',
                'code': 'BRON',
                'duration': 30,
                'price': 500.0,
                'description': '支气管镜检查',
                'preparation': '检查前禁食8小时，禁水4小时',
                'contraindications': '严重呼吸功能不全患者禁忌'
            },
            {
                'name': '胶囊内镜检查',
                'code': 'CAP',
                'duration': 480,
                'price': 2800.0,
                'description': '胶囊内镜检查，可观察全消化道',
                'preparation': '检查前完整肠道准备',
                'contraindications': '消化道狭窄患者禁忌'
            }
        ],
        'LAB': [
            {
                'name': '血常规检查',
                'code': 'CBC',
                'duration': 5,
                'price': 35.0,
                'description': '血细胞分析、血红蛋白等检查',
                'preparation': '无特殊准备',
                'contraindications': ''
            },
            {
                'name': '生化全套检查',
                'code': 'CHEM',
                'duration': 5,
                'price': 180.0,
                'description': '肝功能、肾功能、血脂等生化指标检查',
                'preparation': '空腹8小时以上',
                'contraindications': ''
            },
            {
                'name': '甲功激素六项',
                'code': 'THY',
                'duration': 10,
                'price': 220.0,
                'description': '甲状腺功能检查',
                'preparation': '建议空腹',
                'contraindications': ''
            },
            {
                'name': '凝血功能检查',
                'code': 'COAG',
                'duration': 10,
                'price': 120.0,
                'description': '凝血功能检查',
                'preparation': '建议空腹',
                'contraindications': ''
            },
            {
                'name': '尿常规检查',
                'code': 'UA',
                'duration': 5,
                'price': 20.0,
                'description': '尿常规检查',
                'preparation': '清洁中段尿',
                'contraindications': ''
            },
            {
                'name': '肿瘤标志物检查',
                'code': 'TUMOR',
                'duration': 10,
                'price': 550.0,
                'description': '多项肿瘤标志物检查',
                'preparation': '建议空腹',
                'contraindications': ''
            }
        ],
        'PATH': [
            {
                'name': 'HE常规切片',
                'code': 'HE',
                'duration': 15,
                'price': 150.0,
                'description': '组织病理学HE染色检查',
                'preparation': '需提供组织标本',
                'contraindications': ''
            },
            {
                'name': '免疫组化检查',
                'code': 'IHC',
                'duration': 15,
                'price': 300.0,
                'description': '免疫组化染色检查',
                'preparation': '需提供组织标本',
                'contraindications': ''
            },
            {
                'name': '术中快速病理',
                'code': 'FROZEN',
                'duration': 30,
                'price': 500.0,
                'description': '手术中快速病理诊断',
                'preparation': '需提供新鲜组织标本',
                'contraindications': ''
            },
            {
                'name': '细胞学检查',
                'code': 'CYTO',
                'duration': 15,
                'price': 100.0,
                'description': '细胞学涂片检查',
                'preparation': '需提供细胞学标本',
                'contraindications': ''
            },
            {
                'name': '特殊染色',
                'code': 'SPECIAL',
                'duration': 20,
                'price': 200.0,
                'description': '特殊染色检查',
                'preparation': '需提供组织切片',
                'contraindications': ''
            }
        ],
        'FUNC': [
            {
                'name': '肺功能检查',
                'code': 'PFT',
                'duration': 20,
                'price': 200.0,
                'description': '肺通气功能和弥散功能检查',
                'preparation': '检查前禁烟2小时，避免剧烈运动',
                'contraindications': '活动性肺结核患者禁忌'
            },
            {
                'name': '脑电图检查',
                'code': 'EEG',
                'duration': 30,
                'price': 180.0,
                'description': '脑电活动检查',
                'preparation': '保证充足睡眠，避免使用影响中枢神经的药物',
                'contraindications': ''
            },
            {
                'name': '动态脑电图检查',
                'code': 'AEEG',
                'duration': 720,
                'price': 500.0,
                'description': '24小时动态脑电图记录',
                'preparation': '保持正常作息，记录日常活动',
                'contraindications': ''
            },
            {
                'name': '视觉诱发电位',
                'code': 'VEP',
                'duration': 30,
                'price': 150.0,
                'description': '视觉诱发电位检查',
                'preparation': '充足睡眠，避免眼部疲劳',
                'contraindications': '光敏性癫痫患者禁忌'
            },
            {
                'name': '听觉诱发电位',
                'code': 'BAEP',
                'duration': 30,
                'price': 150.0,
                'description': '脑干听觉诱发电位检查',
                'preparation': '保持安静配合',
                'contraindications': ''
            },
            {
                'name': '经颅多普勒检查',
                'code': 'TCD',
                'duration': 25,
                'price': 180.0,
                'description': '颅内血管超声检查',
                'preparation': '无特殊准备',
                'contraindications': ''
            }
        ]
    }
    
    # 建立设备和科室的映射
    dept_equip_map = {}
    for equip in equipment:
        if equip.department.code not in dept_equip_map:
            dept_equip_map[equip.department.code] = []
        dept_equip_map[equip.department.code].append(equip)
    
    created_examinations = []
    for dept in departments:
        dept_examinations = examination_data.get(dept.code, [])
        for exam_data in dept_examinations:
            try:
                exam_data['department'] = dept
                exam, created = Examination.objects.get_or_create(
                    code=exam_data['code'],
                    defaults=exam_data
                )
                
                if created:
                    # 关联可用设备
                    dept_equipment = dept_equip_map.get(dept.code, [])
                    exam.equipment_type.set(dept_equipment)
                    logger.info(f"创建检查项目: {exam.name}")
                else:
                    logger.info(f"检查项目已存在: {exam.name}")
                
                created_examinations.append(exam)
            except Exception as e:
                logger.error(f"创建检查项目 {exam_data['name']} 时出错: {str(e)}")
    
    return created_examinations

def generate_medical_record_number():
    """
    生成唯一的医疗记录号
    格式：YYYYMM + 5位序号 + 1位校验位
    例如：20240300001X，其中X为校验位
    """
    current_date = datetime.now()
    year_month = current_date.strftime("%Y%m")
    
    # 获取当前年月下最大的序号
    latest_record = Patient.objects.filter(
        medical_record_number__startswith=year_month
    ).order_by('-medical_record_number').first()
    
    if latest_record and len(latest_record.medical_record_number) >= 11:
        try:
            # 提取序号部分（第7-11位）
            latest_sequence = int(latest_record.medical_record_number[6:11])
            sequence = str(latest_sequence + 1).zfill(5)
        except ValueError:
            sequence = '00001'
    else:
        sequence = '00001'
    
    # 生成基础医疗记录号（不包含校验位）
    base_number = f"{year_month}{sequence}"
    
    # 计算校验位（使用加权因子计算）
    factors = [7, 9, 10, 5, 8, 4, 2, 3, 6, 7, 9]
    checksum = sum(int(a) * b for a, b in zip(base_number, factors)) % 11
    check_digit = 'X' if checksum == 10 else str(checksum)
    
    # 返回完整的医疗记录号
    return f"{base_number}{check_digit}"

def generate_patients(count=1000):
    """生成患者数据"""
    logger.info(f"开始生成 {count} 条患者记录...")
    
    # 定义一些常见病史
    common_medical_histories = [
        '高血压病史10年，规律服用降压药',
        '2型糖尿病病史5年，口服降糖药控制',
        '冠心病病史，曾行支架植入手术',
        '慢性胃炎，长期服用质子泵抑制剂',
        '支气管哮喘，间断使用吸入剂',
        '骨质疏松，定期补充钙剂',
        '甲状腺功能亢进，规律服用甲巯咪唑',
        '类风湿性关节炎，长期服用免疫抑制剂',
        '慢性肾功能不全，定期透析治疗',
        '脑梗塞后遗症，长期服用抗血小板药物'
    ]
    
    # 定义一些常见过敏史
    common_allergies = [
        '对青霉素类抗生素过敏',
        '对碘造影剂过敏',
        '对海鲜过敏',
        '对阿司匹林过敏',
        '对磺胺类药物过敏',
        '对花粉过敏',
        '对乳制品过敏',
        '对某些中药过敏'
    ]
    
    # 定义一些特殊需求
    special_needs_list = [
        '需要轮椅',
        '需要担架',
        '需要陪护',
        '需要翻译',
        '听力障碍需要手语翻译',
        '视力障碍需要引导',
        '行动不便需要协助',
        '需要心理关怀'
    ]

    # 生成年龄分布权重（使老年人和中年人较多）
    age_weights = {
        (18, 30): 0.15,  # 青年人 15%
        (31, 50): 0.35,  # 中年人 35%
        (51, 70): 0.35,  # 中老年人 35%
        (71, 90): 0.15   # 老年人 15%
    }
    
    created_patients = []
    retry_count = 0
    max_retries = 10  # 最大重试次数
    
    while len(created_patients) < count and retry_count < max_retries:
        try:
            # 生成性别（略微偏向女性）
            gender = random.choices(['M', 'F'], weights=[0.48, 0.52])[0]
            
            # 生成姓名（根据性别）
            name = fake.name()
            
            # 根据权重生成年龄段
            age_range = random.choices(list(age_weights.keys()), 
                                    weights=list(age_weights.values()))[0]
            birth_date = fake.date_of_birth(minimum_age=age_range[0], 
                                          maximum_age=age_range[1])
            
            # 生成身份证号（确保与出生日期匹配）
            id_number = fake.ssn()
            
            # 使用新的医疗记录号生成函数
            medical_record_number = generate_medical_record_number()
            
            # 生成电话号码（固定电话或手机号码）
            phone = random.choice([
                fake.phone_number(),
                f"0{random.randint(10,99)}-{random.randint(10000000,99999999)}"
            ])
            
            # 生成地址（添加详细门牌号）
            address = f"{fake.address()} {random.randint(1,999)}号"
            
            # 随机生成优先级（基于实际情况的分布）
            priority_weights = [0.8, 0.15, 0.04, 0.01]  # 正常、优先、紧急、危急
            priority = random.choices([0, 1, 2, 3], weights=priority_weights)[0]
            
            # 生成特殊需求（10%的概率有特殊需求）
            special_needs = ''
            if random.random() < 0.1:
                special_needs = random.choice(special_needs_list)
            
            # 生成病史（30%的概率有病史，可能有多个）
            medical_history = ''
            if random.random() < 0.3:
                num_histories = random.randint(1, 3)
                selected_histories = random.sample(common_medical_histories, num_histories)
                medical_history = '；'.join(selected_histories)
            
            # 生成过敏史（20%的概率有过敏史，可能有多个）
            allergies = ''
            if random.random() < 0.2:
                num_allergies = random.randint(1, 2)
                selected_allergies = random.sample(common_allergies, num_allergies)
                allergies = '；'.join(selected_allergies)
            
            # 创建患者记录
            patient = Patient(
                name=name,
                gender=gender,
                birth_date=birth_date,
                id_number=id_number,
                medical_record_number=medical_record_number,
                phone=phone,
                address=address,
                priority=priority,
                special_needs=special_needs,
                medical_history=medical_history,
                allergies=allergies
            )
            
            # 使用get_or_create来确保不会创建重复记录
            patient, created = Patient.objects.get_or_create(
                medical_record_number=medical_record_number,
                defaults={
                    'name': name,
                    'gender': gender,
                    'birth_date': birth_date,
                    'id_number': id_number,
                    'phone': phone,
                    'address': address,
                    'priority': priority,
                    'special_needs': special_needs,
                    'medical_history': medical_history,
                    'allergies': allergies
                }
            )
            
            if created:
                created_patients.append(patient)
                if len(created_patients) % 100 == 0:
                    logger.info(f"已创建 {len(created_patients)} 条患者记录")
            else:
                retry_count += 1
                logger.warning(f"医疗记录号 {medical_record_number} 已存在，尝试重新生成")
                
        except Exception as e:
            logger.error(f"创建患者记录时出错: {str(e)}")
            retry_count += 1
            continue
        
        if retry_count >= max_retries:
            logger.error("达到最大重试次数，停止生成患者记录")
            break
    
    logger.info(f"成功创建 {len(created_patients)} 条患者记录")
    return created_patients

def generate_base_data():
    """生成所有基础数据"""
    try:
        # 生成科室数据
        logger.info("开始生成科室数据...")
        departments = generate_departments()
        logger.info(f"成功创建 {len(departments)} 个科室")
        
        # 生成设备数据
        logger.info("开始生成设备数据...")
        equipment = generate_equipment(departments)
        logger.info(f"成功创建 {len(equipment)} 个设备")
        
        # 生成检查项目数据
        logger.info("开始生成检查项目数据...")
        examinations = generate_examinations(departments, equipment)
        logger.info(f"成功创建 {len(examinations)} 个检查项目")
        
        # 生成患者数据
        patients = generate_patients(1000)
        
        logger.info("基础数据生成完成！")
        logger.info(f"- 科室数量: {len(departments)}")
        logger.info(f"- 设备数量: {len(equipment)}")
        logger.info(f"- 检查项目数量: {len(examinations)}")
        logger.info(f"- 患者数量: {len(patients)}")
        
    except Exception as e:
        logger.error(f"生成基础数据时出错: {str(e)}")

if __name__ == '__main__':
    generate_base_data() 