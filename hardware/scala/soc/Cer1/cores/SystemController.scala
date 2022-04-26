package elements.soc.cer1

import scala.collection.mutable.ArrayBuffer
import spinal.core._
import spinal.lib._
import spinal.lib.bus.amba3.apb._
import spinal.lib.bus.amba4.axi._
import spinal.lib.bus.misc.SizeMapping
import spinal.lib.com.jtag.Jtag
import nafarr.system.mtimer.{Apb3MachineTimer, MachineTimerCtrl}
import nafarr.system.plic.{Apb3Plic, Plic, PlicCtrl}
import nafarr.peripherals.com.uart.{Apb3Uart, Uart, UartCtrl}
import nafarr.networkonchip.amba4.axi._
import vexriscv._
import vexriscv.plugin._
import zibal.cores.VexRiscvCoreParameter

object SystemController {
  def apply(ramSize: BigInt, parameter: Parameter = Parameter()) =
    new SystemController(ramSize, parameter)

  case class Parameter() {
    val core = VexRiscvCoreParameter.realtime(0xf0000000L).plugins
    val mtimer = MachineTimerCtrl.Parameter.default
    val plic = PlicCtrl.Parameter.default(2)
    val uartStd = UartCtrl.Parameter.full
  }

  case class Io(parameter: Parameter = Parameter()) extends Bundle {
    val uartStd = master(Uart.Io(parameter.uartStd))
  }

  case class SystemController(ramSize: BigInt, parameter: Parameter) extends Component {
    val io = new Bundle {
      val localPort = new Bundle {
        val output = master(Axi4(axi4Config.coreUpsized))
      }
      val external = new Io(parameter)
    }

    val upsizer = Axi4Upsizer(axi4Config.coreSmall, axi4Config.coreUpsized, 4)
    upsizer.io.output <> io.localPort.output

    /* AXI Manager */
    val core = new Area {
      val mtimerInterrupt = Bool
      val globalInterrupt = Bool

      val config = VexRiscvConfig(parameter.core)
      val cpu = new VexRiscv(config)
      var iBus: Axi4ReadOnly = null
      var dBus: Axi4Shared = null
      for (plugin <- config.plugins) plugin match {
        case plugin: IBusSimplePlugin => iBus = plugin.iBus.toAxi4ReadOnly()
        case plugin: IBusCachedPlugin => iBus = plugin.iBus.toAxi4ReadOnly()
        case plugin: DBusSimplePlugin => dBus = plugin.dBus.toAxi4Shared()
        case plugin: DBusCachedPlugin => dBus = plugin.dBus.toAxi4Shared()
        case plugin: CsrPlugin => {
          plugin.externalInterrupt := globalInterrupt
          plugin.timerInterrupt := mtimerInterrupt
        }
        case _ =>
      }
    }

    /* AXI Subordinates */
    val ram = Axi4SharedOnChipRam(
      dataWidth = axi4Config.coreSmall.dataWidth,
      byteCount = ramSize,
      idWidth = 4
    )

    val apbBridge = Axi4SharedToApb3Bridge(
      addressWidth = 20,
      dataWidth = 32,
      idWidth = 4
    )

    /* Generate AXI Crossbar */
    val axiCrossbar = Axi4CrossbarFactory()
    axiCrossbar.addSlave(ram.io.axi, (0xf0000000L, 1 MiB))
    axiCrossbar.addSlave(apbBridge.io.axi, (0xf0100000L, 1 MiB))
    axiCrossbar.addSlave(upsizer.io.input, (0x00000000L, 2 GiB))
    axiCrossbar.addConnections(
      core.iBus -> List(ram.io.axi),
      core.dBus -> List(ram.io.axi, apbBridge.io.axi, upsizer.io.input)
    )
    axiCrossbar.build()

    /* Peripheral IP-Cores */
    val irqMapping = ArrayBuffer[(Int, Bool)]()
    val apbMapping = ArrayBuffer[(Apb3, SizeMapping)]()
    def addApbDevice(port: Apb3, address: BigInt, size: BigInt) {
      apbMapping += port -> (address, size)
    }

    val plicCtrl = Apb3Plic(parameter.plic)
    core.globalInterrupt := plicCtrl.io.interrupt
    addApbDevice(plicCtrl.io.bus, 0xf0000, 64 kB)
    plicCtrl.io.sources(0) := False

    val mtimerCtrl = Apb3MachineTimer(parameter.mtimer)
    core.mtimerInterrupt := mtimerCtrl.io.interrupt
    addApbDevice(mtimerCtrl.io.bus, 0x20000, 4 kB)

    val uartStdCtrl = Apb3Uart(parameter.uartStd)
    uartStdCtrl.io.uart <> io.external.uartStd
    addApbDevice(uartStdCtrl.io.bus, 0x00000, 4 kB)
    plicCtrl.io.sources(1) := uartStdCtrl.io.interrupt

    val apbDecoder = Apb3Decoder(
      master = apbBridge.io.apb,
      slaves = apbMapping
    )
  }

  case class SystemControllerWithMemory(
      ramSize: BigInt,
      memorySize: BigInt,
      parameter: Parameter
  ) extends Component {
    val io = new Bundle {
      val localPort = new Bundle {
        val input = slave(Axi4(axi4Config.coreUpsized))
        val output = master(Axi4(axi4Config.coreUpsized))
      }
      val external = new Io(parameter)
    }

    val downsizer = Axi4Downsizer(axi4Config.coreUpsized, axi4Config.coreSmall)
    downsizer.io.input <> io.localPort.input

    val upsizer = Axi4Upsizer(axi4Config.coreSmall, axi4Config.coreUpsized, 4)
    upsizer.io.output <> io.localPort.output

    /* AXI Manager */
    val core = new Area {
      val mtimerInterrupt = Bool
      val globalInterrupt = Bool

      val config = VexRiscvConfig(parameter.core)
      val cpu = new VexRiscv(config)
      var iBus: Axi4ReadOnly = null
      var dBus: Axi4Shared = null
      for (plugin <- config.plugins) plugin match {
        case plugin: IBusSimplePlugin => iBus = plugin.iBus.toAxi4ReadOnly()
        case plugin: IBusCachedPlugin => iBus = plugin.iBus.toAxi4ReadOnly()
        case plugin: DBusSimplePlugin => dBus = plugin.dBus.toAxi4Shared()
        case plugin: DBusCachedPlugin => dBus = plugin.dBus.toAxi4Shared()
        case plugin: CsrPlugin => {
          plugin.externalInterrupt := globalInterrupt
          plugin.timerInterrupt := mtimerInterrupt
        }
        case _ =>
      }
    }

    /* AXI Subordinates */
    val ram = Axi4SharedOnChipRam(
      dataWidth = axi4Config.coreSmall.dataWidth,
      byteCount = ramSize,
      idWidth = 4
    )

    val socMemory0 = Axi4SharedOnChipRam(
      dataWidth = axi4Config.coreSmall.dataWidth,
      byteCount = memorySize,
      idWidth = 4
    )

    val socMemory1 = Axi4SharedOnChipRam(
      dataWidth = axi4Config.coreSmall.dataWidth,
      byteCount = memorySize,
      idWidth = 4
    )

    val apbBridge = Axi4SharedToApb3Bridge(
      addressWidth = 20,
      dataWidth = 32,
      idWidth = 4
    )

    /* Generate AXI Crossbar */
    val axiCrossbar = Axi4CrossbarFactory()
    axiCrossbar.addSlave(ram.io.axi, (0xf0000000L, 1 MiB))
    axiCrossbar.addSlave(apbBridge.io.axi, (0xf0100000L, 1 MiB))
    axiCrossbar.addSlave(upsizer.io.input, (0x08000000L, 3 GiB))
    axiCrossbar.addSlave(socMemory0.io.axi, (0x00000000L, memorySize))
    axiCrossbar.addSlave(socMemory1.io.axi, (0x00000000L + memorySize, memorySize))
    axiCrossbar.addConnections(
      core.iBus -> List(ram.io.axi),
      core.dBus -> List(ram.io.axi, apbBridge.io.axi, upsizer.io.input),
      downsizer.io.output -> List(socMemory0.io.axi, socMemory1.io.axi)
    )
    axiCrossbar.build()

    /* Peripheral IP-Cores */
    val irqMapping = ArrayBuffer[(Int, Bool)]()
    val apbMapping = ArrayBuffer[(Apb3, SizeMapping)]()
    def addApbDevice(port: Apb3, address: BigInt, size: BigInt) {
      apbMapping += port -> (address, size)
    }

    val plicCtrl = Apb3Plic(parameter.plic)
    core.globalInterrupt := plicCtrl.io.interrupt
    addApbDevice(plicCtrl.io.bus, 0xf0000, 64 kB)
    plicCtrl.io.sources(0) := False

    val mtimerCtrl = Apb3MachineTimer(parameter.mtimer)
    core.mtimerInterrupt := mtimerCtrl.io.interrupt
    addApbDevice(mtimerCtrl.io.bus, 0x20000, 4 kB)

    val uartStdCtrl = Apb3Uart(parameter.uartStd)
    uartStdCtrl.io.uart <> io.external.uartStd
    addApbDevice(uartStdCtrl.io.bus, 0x00000, 4 kB)
    plicCtrl.io.sources(1) := uartStdCtrl.io.interrupt

    val apbDecoder = Apb3Decoder(
      master = apbBridge.io.apb,
      slaves = apbMapping
    )
  }

}

object SystemControllerDemo extends App {
  SpinalVerilog {
    val cd = new ClockingArea(ClockDomain.current.copy(frequency = FixedFrequency(100 MHz))) {
      val top = SystemController(4 KiB)
    }
    cd.top
  }
}
