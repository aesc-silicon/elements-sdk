package elements.soc.cer1

import scala.collection.mutable.ArrayBuffer

import spinal.core._
import spinal.core.sim._
import spinal.sim._
import spinal.lib._
import spinal.lib.bus.amba3.apb._
import spinal.lib.bus.misc.SizeMapping

import nafarr.system.reset._
import nafarr.system.clock._
import nafarr.blackboxes.xilinx.a7._

import zibal.misc._
import zibal.board.{KitParameter, BoardParameter}

import elements.sdk.ElementsApp
import elements.board.Nexys4DDR
import elements.soc.Cer1

case class Nexys4DDRBoard() extends Component {
  val io = new Bundle {
    val clock = inout(Analog(Bool))
    val systemController = new Bundle {
      val uartStd = new Bundle {
        val txd = inout(Analog(Bool))
        val rxd = inout(Analog(Bool))
        val rts = inout(Analog(Bool))
        val cts = inout(Analog(Bool))
      }
    }
    val computingA = new Bundle {
      val uartStd = new Bundle {
        val txd = inout(Analog(Bool))
        val rxd = inout(Analog(Bool))
        val rts = inout(Analog(Bool))
        val cts = inout(Analog(Bool))
      }
    }
    val computingB = new Bundle {
      val uartStd = new Bundle {
        val txd = inout(Analog(Bool))
        val rxd = inout(Analog(Bool))
        val rts = inout(Analog(Bool))
        val cts = inout(Analog(Bool))
      }
    }
    val peripheralA = new Bundle {
      val gpioA = Vec(inout(Analog(Bool())), 8)
      val gpioB = Vec(inout(Analog(Bool())), 8)
    }
  }
  val top = Nexys4DDRTop()
  val analogFalse = Analog(Bool)
  analogFalse := False
  val analogTrue = Analog(Bool)
  analogTrue := True

  top.io.clock.PAD := io.clock

  top.io.systemController.uartStd.rxd.PAD := io.systemController.uartStd.rxd
  io.systemController.uartStd.txd := top.io.systemController.uartStd.txd.PAD
  top.io.systemController.uartStd.cts.PAD := io.systemController.uartStd.cts
  io.systemController.uartStd.rts := top.io.systemController.uartStd.rts.PAD

  top.io.computingA.uartStd.rxd.PAD := io.computingA.uartStd.rxd
  io.computingA.uartStd.txd := top.io.computingA.uartStd.txd.PAD
  top.io.computingA.uartStd.cts.PAD := io.computingA.uartStd.cts
  io.computingA.uartStd.rts := top.io.computingA.uartStd.rts.PAD

  top.io.computingB.uartStd.rxd.PAD := io.computingB.uartStd.rxd
  io.computingB.uartStd.txd := top.io.computingB.uartStd.txd.PAD
  top.io.computingB.uartStd.cts.PAD := io.computingB.uartStd.cts
  io.computingB.uartStd.rts := top.io.computingB.uartStd.rts.PAD

  for (index <- 0 until 8) {
    io.peripheralA.gpioA(index) <> top.io.peripheralA.gpioA(index).PAD
    io.peripheralA.gpioB(index) <> top.io.peripheralA.gpioB(index).PAD
  }

  val baudPeriod = top.top.soc.chipletSystemController.core.parameter.uartStd.init.getBaudPeriod()

  def simHook() {
    for ((domain, index) <- top.clocks.zipWithIndex) {
      val clockDomain = top.clockCtrl.getClockDomainByName(domain.name)
      SimulationHelper.generateEndlessClock(clockDomain.clock, domain.frequency)
    }
  }
}

case class Nexys4DDRTop() extends Component {
  val resets = List[ResetParameter](ResetParameter("system", 64))
  val clocks = List[ClockParameter](ClockParameter("system", 50 MHz, "system"))

  val kitParameter = KitParameter(resets, clocks)
  val boardParameter = Nexys4DDR.Parameter(kitParameter)

  val io = new Bundle {
    val clock = XilinxCmosIo("E3").clock(boardParameter.getOscillatorFrequency)
    val systemController = new Bundle {
      val uartStd = new Bundle {
        val txd = XilinxCmosIo("D4")
        val rxd = XilinxCmosIo("C4")
        val rts = XilinxCmosIo("D3")
        val cts = XilinxCmosIo("E5")
      }
    }
    val computingA = new Bundle {
      val uartStd = new Bundle {
        val txd = XilinxCmosIo("C17")
        val rxd = XilinxCmosIo("D18")
        val rts = XilinxCmosIo("E18")
        val cts = XilinxCmosIo("G17")
      }
    }
    val computingB = new Bundle {
      val uartStd = new Bundle {
        val txd = XilinxCmosIo("D17")
        val rxd = XilinxCmosIo("E17")
        val rts = XilinxCmosIo("F18")
        val cts = XilinxCmosIo("G18")
      }
    }
    val peripheralA = new Bundle {
      val gpioA = Vec(
        XilinxCmosIo("H17"),
        XilinxCmosIo("K15"),
        XilinxCmosIo("J13"),
        XilinxCmosIo("N14"),
        XilinxCmosIo("R18"),
        XilinxCmosIo("V17"),
        XilinxCmosIo("U17"),
        XilinxCmosIo("U16")
      )
      val gpioB = Vec(
        XilinxCmosIo("V16"),
        XilinxCmosIo("T15"),
        XilinxCmosIo("U14"),
        XilinxCmosIo("T16"),
        XilinxCmosIo("V15"),
        XilinxCmosIo("V14"),
        XilinxCmosIo("V12"),
        XilinxCmosIo("V11")
      )
    }
  }

  val clock = Bool()
  io.clock <> IBUF(clock)

  val resetCtrl = ResetControllerCtrl(ResetControllerCtrl.Parameter(resets))
  resetCtrl.buildXilinx(clock)
  resetCtrl.io.config.enable := U(resets.length bits, default -> True)
  resetCtrl.io.config.trigger := U(0, resets.length bits)
  resetCtrl.io.config.acknowledge := False

  val clockCtrl = ClockControllerCtrl(ClockControllerCtrl.Parameter(clocks), resetCtrl)
  clockCtrl.buildXilinxPll(clock, Nexys4DDR.oscillatorFrequency, List("system"), 10)

  val top = new ClockingArea(clockCtrl.getClockDomainByName("system")) {
    val soc = Cer1()
  }

  io.systemController.uartStd.txd <> OBUF(top.soc.io.systemController.uartStd.txd)
  io.systemController.uartStd.rxd <> IBUF(top.soc.io.systemController.uartStd.rxd)
  io.systemController.uartStd.rts <> OBUF(top.soc.io.systemController.uartStd.rts)
  io.systemController.uartStd.cts <> IBUF(top.soc.io.systemController.uartStd.cts)

  io.computingA.uartStd.txd <> OBUF(top.soc.io.computingA.uartStd.txd)
  io.computingA.uartStd.rxd <> IBUF(top.soc.io.computingA.uartStd.rxd)
  io.computingA.uartStd.rts <> OBUF(top.soc.io.computingA.uartStd.rts)
  io.computingA.uartStd.cts <> IBUF(top.soc.io.computingA.uartStd.cts)

  io.computingB.uartStd.txd <> OBUF(top.soc.io.computingB.uartStd.txd)
  io.computingB.uartStd.rxd <> IBUF(top.soc.io.computingB.uartStd.rxd)
  io.computingB.uartStd.rts <> OBUF(top.soc.io.computingB.uartStd.rts)
  io.computingB.uartStd.cts <> IBUF(top.soc.io.computingB.uartStd.cts)

  for (index <- 0 until 8) {
    io.peripheralA.gpioA(index) <> IOBUF(top.soc.io.peripheralA.gpioA.pins(index))
    io.peripheralA.gpioB(index) <> IOBUF(top.soc.io.peripheralA.gpioB.pins(index))
  }
}

object Nexys4DDRPrepare extends ElementsApp {
  elementsConfig.genFPGASpinalConfig.generateVerilog {
    val top = Nexys4DDRTop()

    val systemController = new Area {
      val core = top.top.soc.chipletSystemController.core

      val header = BaremetalTools.Header(elementsConfig, "systemcontroller0")
      header.generate(
        core.axiCrossbar.slavesConfigs,
        core.apbBridge.io.axi,
        core.apbMapping,
        core.irqMapping
      )
    }

    val computingA = new Area {
      val core = top.top.soc.chipletComputingA.core
      val peripheral = top.top.soc.chipletPeripheralA.core
      val apbMapping = ArrayBuffer[(Apb3, SizeMapping)]()

      apbMapping += peripheral.gpioACtrl.io.bus -> (0x00000, 4 kB)
      apbMapping += core.privateApb.uartStdCtrl.io.bus -> (0x10000, 4 kB)

      val board =
        ZephyrTools.Board(elementsConfig, "zephyr0", "internal/zephyr-samples/startup/mtimer/")
      board.storage.add("include", "hardware")
      board.storage.dump()
      board.addLed("heartbeat", peripheral.gpioACtrl, 0)
      board.addLed("ok", peripheral.gpioACtrl, 1)
      board.addLed("error", peripheral.gpioACtrl, 2)
      board.generateDeviceTree(core.privateApb.uartStdCtrl)
      board.generateKconfig()
      board.generateDefconfig(apbMapping, top.clockCtrl.getClockDomainByName("system"))
    }

    val computingB = new Area {
      val core = top.top.soc.chipletComputingB.core
      val peripheral = top.top.soc.chipletPeripheralA.core
      val apbMapping = ArrayBuffer[(Apb3, SizeMapping)]()

      apbMapping += peripheral.gpioBCtrl.io.bus -> (0x00000, 4 kB)
      apbMapping += core.privateApb.uartStdCtrl.io.bus -> (0x10000, 4 kB)

      val board =
        ZephyrTools.Board(elementsConfig, "zephyr1", "internal/zephyr-samples/startup/mtimer/")
      board.storage.add("include", "hardware")
      board.storage.dump()
      board.addLed("heartbeat", peripheral.gpioBCtrl, 0)
      board.addLed("ok", peripheral.gpioBCtrl, 1)
      board.addLed("error", peripheral.gpioBCtrl, 2)
      board.generateDeviceTree(core.privateApb.uartStdCtrl)
      board.generateKconfig()
      board.generateDefconfig(apbMapping, top.clockCtrl.getClockDomainByName("system"))
    }

    val xdc = XilinxTools.Xdc(elementsConfig)
    top.clockCtrl.generatedClocks foreach { clock => xdc.addGeneratedClock(clock) }
    xdc.generate(top.io)

    top
  }
}

object Nexys4DDRGenerate extends ElementsApp {
  elementsConfig.genFPGASpinalConfig.generateVerilog {
    val top = Nexys4DDRTop()

    val scCore = top.top.soc.chipletSystemController.core
    BinTools.initRam(scCore.ram.ram, elementsConfig.swStorageBaremetalImage("systemcontroller0"))
    BinTools.initRam(scCore.socMemory0.ram, elementsConfig.swStorageZephyrBinary("zephyr0"))
    BinTools.initRam(scCore.socMemory1.ram, elementsConfig.swStorageZephyrBinary("zephyr1"))

    top
  }
}

object Nexys4DDRSimulate extends ElementsApp {
  val compiled = elementsConfig.genFPGASimConfig.compile {
    val board = Nexys4DDRBoard()

    val scCore = board.top.top.soc.chipletSystemController.core
    BinTools.initRam(scCore.ram.ram, elementsConfig.swStorageBaremetalImage("systemcontroller0"))
    BinTools.initRam(scCore.socMemory0.ram, elementsConfig.swStorageZephyrBinary("zephyr0"))
    BinTools.initRam(scCore.socMemory1.ram, elementsConfig.swStorageZephyrBinary("zephyr1"))

    for (domain <- board.top.clocks) {
      board.top.clockCtrl.getClockDomainByName(domain.name).clock.simPublic()
    }
    board
  }
  simType match {
    case "simulate" =>
      compiled.doSimUntilVoid("simulate") { dut =>
        dut.simHook()
        val testCases = TestCases()
        testCases.addClock(dut.io.clock, Nexys4DDR.oscillatorFrequency, 20 ms)
        testCases.dump(dut.io.systemController.uartStd.txd, dut.baudPeriod)
        testCases.dump(dut.io.computingA.uartStd.txd, dut.baudPeriod)
        testCases.dump(dut.io.computingB.uartStd.txd, dut.baudPeriod)
      }
    case _ =>
      println(s"Unknown simulation ${simType}")
  }
}
