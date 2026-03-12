# 教务系统选课 API 分析报告

生成时间: 2026-03-12

## 概述

本报告分析了东莞理工学院教务系统（jwx.dgut.edu.cn）的选课相关网络请求。

## 重要约束

⚠️ **安全限制**:
- **禁止退选操作**: 不得调用退选相关的 API
- **学分限制**: 当前已选 2 学分，只能选择 1 学分的课程（总限制 3 学分）

---

## API 端点分析

### 1. 课程列表查询 (分页切换)

**端点**: `POST /xsxkkc/xsxkGgxxkxk`

**用途**: 获取公共选修课列表（支持分页）

**请求参数**:
```
查询参数:
- sfym: false (是否预约)
- sfct: true (是否冲突检测)
- sfxx: true (是否显示详细信息)

POST 数据 (DataTables 格式):
- sEcho: 5 (请求序号)
- iColumns: 13 (列数)
- iDisplayStart: 40 (起始记录，用于分页)
- iDisplayLength: 10 (每页显示数量)
- mDataProp_0 到 mDataProp_12: 列属性映射
  - kch: 课程号
  - kcmc: 课程名称
  - xf: 学分
  - skls: 授课老师
  - sksj: 上课时间
  - skdd: 上课地点
  - xqmc: 校区名称
  - xkrs: 选课人数
  - syrs: 剩余人数
  - skfsmc: 授课方式名称
  - ctsm: 冲突说明
  - szkcflmc: 所在课程分类名称
  - czOper: 操作
```

**响应数据结构**:
```json
{
  "aaData": [
    {
      "kch": "课程号",
      "kcmc": "课程名称",
      "xf": "学分",
      "skls": "授课老师",
      "sksj": "上课时间",
      "skdd": "上课地点",
      "xqmc": "校区",
      "xkrs": "选课人数",
      "syrs": "剩余人数",
      "kcid": "课程ID (重要!)",
      "jx0404id": "教学班ID (重要!)"
    }
  ],
  "iTotalRecords": 总记录数,
  "iTotalDisplayRecords": 显示记录数
}
```

**关键字段**:
- `kcid`: 课程唯一标识符
- `jx0404id`: 教学班ID
- `syrs`: 剩余人数（必须 > 0 才能选课）
- `xf`: 学分（当前只能选 1 学分的课程）

---

### 2. 选课操作 ⭐

**端点**: `GET /xsxkkc/ggxxkxkOper`

**用途**: 执行选课操作

**请求参数**:
```
查询参数:
- kcid: 课程ID (从课程列表获取)
- cfbs: null (冲突标识)
- jx0404id: 教学班ID (从课程列表获取)
```

**示例**:
```
GET /xsxkkc/ggxxkxkOper?kcid=5CDB3E058D84436EA3175F09C9DE1B75&cfbs=null&jx0404id=202520262009064
```

**响应数据**:
```json
{
  "success": true,
  "message": "选课成功",
  "jfViewStr": ""
}
```

**可能的响应状态**:
- `success: true` - 选课成功
- `success: false` - 选课失败（可能原因：人数已满、学分超限、时间冲突等）

---

### 3. 已选课程查询

**端点**: `GET /xsxkjg/comeXkjglb`

**用途**: 查看已选课程列表

**说明**: 用于确认选课结果和当前学分统计

---

## 选课流程

```
1. 查询课程列表
   POST /xsxkkc/xsxkGgxxkxk
   ↓
2. 筛选符合条件的课程
   - 学分 = 1
   - 剩余人数 > 0
   - 无时间冲突
   ↓
3. 执行选课
   GET /xsxkkc/ggxxkxkOper?kcid=XXX&cfbs=null&jx0404id=YYY
   ↓
4. 验证结果
   GET /xsxkjg/comeXkjglb
```

---

## 重要发现

### 1. 认证机制
- 需要有效的 Cookie (JSESSIONID)
- 需要通过 CAS 认证

### 2. 并发控制
- 选课接口可能有并发限制
- 建议添加请求间隔（避免被限流）

### 3. 数据格式
- 课程列表使用 DataTables 格式（jQuery 插件）
- 选课操作使用简单的 GET 请求

### 4. 学分计算
- 当前已选: 2 学分
- 总限制: 3 学分
- **只能选择 1 学分的课程**

---

## 实现建议

### 安全检查清单
- [ ] 验证课程学分 = 1
- [ ] 检查剩余人数 > 0
- [ ] 确认无时间冲突 (ctsm 字段)
- [ ] 禁用退选功能
- [ ] 添加选课确认提示

### 错误处理
- 网络超时重试
- 选课失败提示
- 学分超限警告

### 性能优化
- 缓存课程列表
- 批量查询优化
- 请求频率控制

---

## 附录

### 相关文件
- HAR 文件位置: `developer/network/`
- 分析脚本: `script/network/analyze_har.py`
- JSON 数据: `docs/developer/network/har_analysis.json`

### 参考链接
- 选课页面: https://jwx.dgut.edu.cn/xsxkkc/getGgxxk
