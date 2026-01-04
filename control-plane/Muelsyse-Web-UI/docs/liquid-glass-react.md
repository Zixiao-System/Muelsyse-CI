# liquid-glass-react 使用文档

> Apple Liquid Glass 风格玻璃效果 React 组件库

## 概述

`liquid-glass-react` 是一个实现 Apple Liquid Glass 设计风格的 React 组件库，提供真实的玻璃折射、弯曲效果和鼠标交互响应。

**项目依赖版本:** ^1.1.1

## 安装

项目已安装此依赖，无需额外操作。如需在其他项目使用：

```bash
npm install liquid-glass-react
```

**Peer Dependencies:**
- React >= 19
- React-DOM >= 19

## 基础用法

### 引入组件

```tsx
import LiquidGlass from 'liquid-glass-react'
```

### 基本示例

```tsx
function App() {
  return (
    <LiquidGlass>
      <div className="p-6">
        <h2>你的内容</h2>
        <p>这里的内容将具有液态玻璃效果</p>
      </div>
    </LiquidGlass>
  )
}
```

## Props 属性说明

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `children` | `ReactNode` | **必填** | 玻璃容器内的子元素 |
| `displacementScale` | `number` | `70` | 位移效果强度 |
| `blurAmount` | `number` | `0.0625` | 磨砂/模糊程度 |
| `saturation` | `number` | `140` | 颜色饱和度 |
| `aberrationIntensity` | `number` | `2` | 色差强度 |
| `elasticity` | `number` | `0.15` | 弹性程度 (0=刚性, 值越高越弹) |
| `cornerRadius` | `number` | `999` | 圆角半径 (像素) |
| `className` | `string` | `""` | 额外的 CSS 类名 |
| `padding` | `string` | — | CSS 内边距值 |
| `style` | `CSSProperties` | — | 内联样式 |
| `overLight` | `boolean` | `false` | 是否在浅色背景上使用 |
| `onClick` | `() => void` | — | 点击事件处理函数 |
| `mouseContainer` | `RefObject<HTMLElement>` | `null` | 鼠标追踪的父容器引用 |
| `mode` | `string` | `"standard"` | 折射模式 |
| `globalMousePos` | `{ x: number; y: number }` | — | 手动控制鼠标位置 |
| `mouseOffset` | `{ x: number; y: number }` | — | 鼠标位置偏移调整 |

## 折射模式 (mode)

组件支持 4 种视觉效果模式：

| 模式 | 说明 |
|------|------|
| `"standard"` | 标准液态玻璃折射效果 (默认) |
| `"polar"` | 极坐标折射效果 |
| `"prominent"` | 更显著的玻璃效果 |
| `"shader"` | 基于着色器的最精确效果 (性能消耗较高) |

## 使用示例

### 1. 玻璃按钮

```tsx
<LiquidGlass
  displacementScale={64}
  blurAmount={0.1}
  saturation={130}
  aberrationIntensity={2}
  elasticity={0.35}
  cornerRadius={100}
  padding="12px 24px"
  onClick={() => console.log('按钮被点击')}
>
  <span className="text-white font-medium">点击我</span>
</LiquidGlass>
```

### 2. 玻璃卡片

```tsx
<LiquidGlass
  displacementScale={50}
  blurAmount={0.08}
  cornerRadius={24}
  padding="24px"
  className="max-w-md"
>
  <h3 className="text-xl font-bold mb-2">玻璃卡片标题</h3>
  <p className="text-gray-700">这是一个具有液态玻璃效果的卡片组件。</p>
</LiquidGlass>
```

### 3. 容器级鼠标追踪

当需要玻璃效果响应更大区域内的鼠标移动时，使用 `mouseContainer` 属性：

```tsx
import { useRef } from 'react'
import LiquidGlass from 'liquid-glass-react'

function GlassHero() {
  const containerRef = useRef<HTMLDivElement>(null)

  return (
    <div
      ref={containerRef}
      className="w-full h-screen relative"
      style={{ backgroundImage: 'url(/hero-bg.jpg)' }}
    >
      <LiquidGlass
        mouseContainer={containerRef}
        elasticity={0.3}
        displacementScale={60}
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)'
        }}
      >
        <div className="p-8">
          <h1 className="text-3xl">玻璃效果响应整个容器的鼠标移动</h1>
        </div>
      </LiquidGlass>
    </div>
  )
}
```

### 4. 不同模式对比

```tsx
// 标准模式
<LiquidGlass mode="standard">
  <p>标准折射效果</p>
</LiquidGlass>

// 极坐标模式
<LiquidGlass mode="polar">
  <p>极坐标折射效果</p>
</LiquidGlass>

// 显著模式
<LiquidGlass mode="prominent">
  <p>更强烈的玻璃效果</p>
</LiquidGlass>

// 着色器模式 (最精确但性能消耗更高)
<LiquidGlass mode="shader">
  <p>着色器渲染效果</p>
</LiquidGlass>
```

### 5. 导航菜单

```tsx
<LiquidGlass
  cornerRadius={16}
  blurAmount={0.05}
  padding="8px"
>
  <nav className="flex gap-4">
    <a href="/" className="px-4 py-2 hover:bg-white/20 rounded-lg">首页</a>
    <a href="/about" className="px-4 py-2 hover:bg-white/20 rounded-lg">关于</a>
    <a href="/contact" className="px-4 py-2 hover:bg-white/20 rounded-lg">联系</a>
  </nav>
</LiquidGlass>
```

### 6. 浅色背景使用

```tsx
<div className="bg-white p-8">
  <LiquidGlass overLight={true} cornerRadius={20}>
    <p className="p-4 text-gray-800">
      在浅色背景上使用时，启用 overLight 可获得更好的效果
    </p>
  </LiquidGlass>
</div>
```

## 与项目集成

### 在 Welcome 组件中使用

```tsx
// app/welcome/welcome.tsx
import LiquidGlass from 'liquid-glass-react'
import logoDark from "./logo-dark.svg"
import logoLight from "./logo-light.svg"

export function Welcome() {
  return (
    <main className="flex items-center justify-center pt-16 pb-4">
      <div className="flex-1 flex flex-col items-center gap-16 min-h-0">
        <header className="flex flex-col items-center gap-9">
          <LiquidGlass cornerRadius={24} padding="16px">
            <div className="w-[500px] max-w-[100vw] p-4">
              <img
                src={logoLight}
                alt="Logo"
                className="block w-full dark:hidden"
              />
              <img
                src={logoDark}
                alt="Logo"
                className="hidden w-full dark:block"
              />
            </div>
          </LiquidGlass>
        </header>

        <div className="max-w-[300px] w-full space-y-6 px-4">
          <LiquidGlass
            cornerRadius={24}
            blurAmount={0.06}
            className="p-6 space-y-4"
          >
            <p className="leading-6 text-gray-700 dark:text-gray-200 text-center">
              下一步是什么?
            </p>
            {/* 导航链接 */}
          </LiquidGlass>
        </div>
      </div>
    </main>
  )
}
```

## 参数调优指南

### 磨砂效果

```tsx
// 轻微磨砂
<LiquidGlass blurAmount={0.03} />

// 中等磨砂 (默认)
<LiquidGlass blurAmount={0.0625} />

// 强烈磨砂
<LiquidGlass blurAmount={0.15} />
```

### 弹性效果

```tsx
// 刚性 (无弹性)
<LiquidGlass elasticity={0} />

// 轻微弹性 (默认)
<LiquidGlass elasticity={0.15} />

// 高弹性 (果冻效果)
<LiquidGlass elasticity={0.5} />
```

### 位移强度

```tsx
// 轻微位移
<LiquidGlass displacementScale={30} />

// 标准位移 (默认)
<LiquidGlass displacementScale={70} />

// 强烈位移
<LiquidGlass displacementScale={120} />
```

## 浏览器兼容性

| 浏览器 | 支持程度 |
|--------|----------|
| Chrome / Chromium | 完全支持 |
| Edge | 完全支持 |
| Safari | 部分支持 (位移效果不可见) |
| Firefox | 部分支持 (位移效果不可见) |

**注意:** Safari 和 Firefox 仅部分支持该效果，位移效果将不可见。建议在这些浏览器中提供优雅降级方案。

## TypeScript 类型

```typescript
interface LiquidGlassProps {
  children: React.ReactNode;
  displacementScale?: number;
  blurAmount?: number;
  saturation?: number;
  aberrationIntensity?: number;
  elasticity?: number;
  cornerRadius?: number;
  className?: string;
  padding?: string;
  style?: React.CSSProperties;
  mode?: "standard" | "polar" | "prominent" | "shader";
  overLight?: boolean;
  globalMousePos?: { x: number; y: number };
  mouseOffset?: { x: number; y: number };
  mouseContainer?: React.RefObject<HTMLElement | null> | null;
  onClick?: () => void;
}
```

## 性能建议

1. **避免在列表中大量使用** - 每个组件都有独立的着色器渲染开销
2. **优先使用 standard 模式** - shader 模式性能消耗最高
3. **合理设置圆角** - 过大的 cornerRadius 可能影响渲染性能
4. **使用 mouseContainer** - 在需要大范围鼠标追踪时，避免频繁更新

## 参考链接

- [GitHub 仓库](https://github.com/rdev/liquid-glass-react)
- [npm 包](https://www.npmjs.com/package/liquid-glass-react)

---

*文档生成日期: 2026-01-04*
